// calibration_fsm.c
//
// Waveform Brain calibration FSM.
//
// v0.18 upgrade:
//   - Adds telemetry-window helpers.
//   - Adds alpha grid-search tuning using syndrome flip-rate minimization.
//   - Adds settle windows after register writes to avoid measuring stale pipeline data.
//   - Keeps LO phase and lattice scale as explicit integration TODOs because those
//     require board-specific DAC/RFDC control not present in this source tree.

#include <stdint.h>
#include <stdbool.h>
#include "registers.h"

// Replace this base address with the address assigned in the Vivado address map.
#ifndef WB_REG_BASE_ADDR
#define WB_REG_BASE_ADDR 0x40000000u
#endif

static volatile uint32_t *const reg_base = (uint32_t *)WB_REG_BASE_ADDR;

static inline void wb_write(uint32_t offset, uint32_t value)
{
    reg_base[offset >> 2] = value;
}

static inline uint32_t wb_read(uint32_t offset)
{
    return reg_base[offset >> 2];
}

static inline void wb_commit_config(void)
{
    wb_write(WB_REG_CFG_APPLY, WB_CFG_APPLY_COMMIT);
}

static void wb_delay_cycles(volatile uint32_t cycles)
{
    while (cycles--)
    {
        __asm__ volatile("nop");
    }
}

static void wb_clear_faults(void)
{
    wb_write(WB_REG_CLEAR_FAULTS, 1u);
}

static void wb_telem_clear_total(void)
{
    wb_write(WB_REG_TELEM_CTRL, WB_TELEM_CTRL_CLEAR_TOTAL);
}

static void wb_telem_start(uint32_t window_cycles)
{
    wb_write(WB_REG_TELEM_WINDOW, window_cycles);
    wb_write(WB_REG_TELEM_CTRL, WB_TELEM_CTRL_START);
}

static bool wb_telem_wait_done(uint32_t timeout_cycles)
{
    while (timeout_cycles--)
    {
        uint32_t st = wb_read(WB_REG_TELEM_STATUS);
        if (st & WB_TELEM_STATUS_DONE)
        {
            return true;
        }
    }
    return false;
}

static uint32_t wb_measure_flip_delta(uint32_t window_cycles, uint32_t settle_cycles, bool *ok)
{
    if (settle_cycles != 0u)
    {
        wb_delay_cycles(settle_cycles);
    }

    wb_telem_start(window_cycles);
    if (!wb_telem_wait_done(window_cycles + (window_cycles >> 2) + 10000u))
    {
        if (ok)
        {
            *ok = false;
        }
        return 0xFFFFFFFFu;
    }

    if (ok)
    {
        *ok = true;
    }
    return wb_read(WB_REG_TELEM_FLIPS_DELTA);
}

typedef struct
{
    uint32_t alpha;
    uint32_t score;
    bool valid;
} wb_alpha_result_t;

static wb_alpha_result_t wb_tune_alpha_grid(
    uint32_t alpha_min,
    uint32_t alpha_max,
    uint32_t alpha_step,
    uint32_t window_cycles,
    uint32_t settle_cycles)
{
    wb_alpha_result_t best = {
        .alpha = alpha_min,
        .score = 0xFFFFFFFFu,
        .valid = false,
    };

    if (alpha_step == 0u)
    {
        alpha_step = 1u;
    }

    for (uint32_t alpha = alpha_min; alpha <= alpha_max; alpha += alpha_step)
    {
        bool ok = false;
        wb_write(WB_REG_ALPHA, alpha);
        wb_commit_config();

        uint32_t flips = wb_measure_flip_delta(window_cycles, settle_cycles, &ok);
        if (ok && flips < best.score)
        {
            best.alpha = alpha;
            best.score = flips;
            best.valid = true;
        }

        if (alpha > (0xFFFFFFFFu - alpha_step))
        {
            break;
        }
    }

    if (best.valid)
    {
        wb_write(WB_REG_ALPHA, best.alpha);
        wb_commit_config();
    }

    return best;
}

typedef enum
{
    FSM_IDLE,
    FSM_ALIGN,
    FSM_LATENCY_MEAS,
    FSM_RAW_STREAM,
    FSM_LO_SWEEP,
    FSM_LO_LOCK,
    FSM_SCALE_SWEEP,
    FSM_ALPHA_TUNE,
    FSM_STREAM,
    FSM_FAULT
} fsm_state_t;

void run_calibration_fsm(void)
{
    fsm_state_t state = FSM_IDLE;

    const uint32_t telem_window = WB_DEFAULT_TELEM_WINDOW;
    const uint32_t settle_cycles = 4096u;

    while (1)
    {
        switch (state)
        {
        case FSM_IDLE:
            wb_clear_faults();
            wb_telem_clear_total();
            state = FSM_ALIGN;
            break;

        case FSM_ALIGN:
            // Board-specific hook:
            //   trigger RFDC/JESD/capture alignment and wait for status bits.
            // Current source tree does not define those status bits yet.
            state = FSM_LATENCY_MEAS;
            break;

        case FSM_LATENCY_MEAS:
            // Board-specific hook:
            //   enable PRBS, capture deterministic latency, verify cold-boot stability.
            // Do not enable optics based only on this placeholder transition.
            state = FSM_RAW_STREAM;
            break;

        case FSM_RAW_STREAM:
            // Board-specific hook:
            //   stream raw ADC data to establish electronic noise and shot-noise references.
            state = FSM_LO_SWEEP;
            break;

        case FSM_LO_SWEEP:
            // Board-specific hook:
            //   sweep LO/EOM phase using DAC control not included in this scaffold.
            state = FSM_LO_LOCK;
            break;

        case FSM_LO_LOCK:
            // Board-specific hook:
            //   close slow LO phase loop using variance metric.
            state = FSM_SCALE_SWEEP;
            break;

        case FSM_SCALE_SWEEP:
            // Board-specific hook:
            //   sweep DELTA_ADC_Q / INV_DELTA_Q using histogram or flip-rate score.
            state = FSM_ALPHA_TUNE;
            break;

        case FSM_ALPHA_TUNE:
        {
            wb_alpha_result_t result = wb_tune_alpha_grid(
                WB_DEFAULT_ALPHA_MIN,
                WB_DEFAULT_ALPHA_MAX,
                WB_DEFAULT_ALPHA_STEP,
                telem_window,
                settle_cycles);

            state = result.valid ? FSM_STREAM : FSM_FAULT;
            break;
        }

        case FSM_STREAM:
            // Normal operation. Firmware may periodically re-run a narrow alpha
            // search or monitor health counters for drift.
            if (wb_read(WB_REG_FAULT_FLAGS) != 0u)
            {
                state = FSM_FAULT;
            }
            break;

        case FSM_FAULT:
        default:
            // Hold here until external supervisor clears or resets.
            // Do not auto-reenable optics/corrections from a safety fault.
            while (1)
            {
                wb_delay_cycles(100000u);
            }
        }
    }
}
