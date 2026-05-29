// registers.h
// Defines register offsets and bitfields for the Waveform Brain AXI-Lite register file.

#ifndef WAVEFORM_REGISTERS_H
#define WAVEFORM_REGISTERS_H

// Register offsets (byte address)
#define WB_REG_BUILD_ID 0x00
#define WB_REG_STATUS 0x04
#define WB_REG_FAULT_FLAGS 0x08
#define WB_REG_PRBS_ENABLE 0x0C
#define WB_REG_INV_DELTA_Q 0x10
#define WB_REG_DELTA_ADC_Q 0x14
#define WB_REG_COEFF0 0x18
#define WB_REG_COEFF1 0x1C
#define WB_REG_COEFF2 0x20
#define WB_REG_COEFF3 0x24
#define WB_REG_ALPHA 0x28
#define WB_REG_KILL_THRESHOLD 0x2C
#define WB_REG_CLEAR_FAULTS 0x30

// Telemetry control/status registers
#define WB_REG_TELEM_CTRL 0x34
#define WB_REG_TELEM_WINDOW 0x38
#define WB_REG_TELEM_STATUS 0x3C
#define WB_REG_TELEM_FLIPS_DELTA 0x40
#define WB_REG_TELEM_TOTAL_FLIPS 0x44

// Health monitor status/counters (read only)
#define WB_REG_HEALTH_STATUS 0x48
#define WB_REG_HEALTH_SAFETY_TRIPS 0x4C
#define WB_REG_HEALTH_AXIS_STALLS 0x50
#define WB_REG_HEALTH_DEC_VALID 0x54
#define WB_REG_HEALTH_TELEM_DONE 0x58
#define WB_REG_AXIS_FIFO_LEVEL 0x5C
#define WB_REG_AXIS_FIFO_OVERFLOW 0x60
#define WB_REG_AXIS_FIFO_STALLS 0x64
#define WB_REG_AXIS_FRAME_DROPS 0x68
#define WB_REG_AXIS_SEQUENCE 0x6C
#define WB_REG_CFG_APPLY 0x70

// Telemetry control bits
#define WB_TELEM_CTRL_START (1u << 0)
#define WB_TELEM_CTRL_CLEAR_TOTAL (1u << 1)

// Config apply bits
#define WB_CFG_APPLY_COMMIT (1u << 0)

// Telemetry status bits
#define WB_TELEM_STATUS_ACTIVE (1u << 0)
#define WB_TELEM_STATUS_DONE (1u << 1)

// Suggested defaults
#define WB_DEFAULT_TELEM_WINDOW 1000000u
#define WB_DEFAULT_ALPHA_MIN 16u
#define WB_DEFAULT_ALPHA_MAX 4096u
#define WB_DEFAULT_ALPHA_STEP 16u

#endif // WAVEFORM_REGISTERS_H
