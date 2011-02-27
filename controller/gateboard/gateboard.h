#include "HardwareSerial.h"

#define LOG(s) Serial.println(s);

#define GB_BOARDNAME_MAXLEN   8

#define GBM_HELLO_ID      0x01
#define GBM_HELLO_TAG_PROTOCOL_VERSION  0x01
#define GBM_HELLO_TAG_FIRMWARE_VERSION  0x01

#define GBM_OUTPUT_STATUS 0x12
#define GBM_OUTPUT_STATUS_TAG_OUTPUT_NAME  0x01
#define GBM_OUTPUT_STATUS_TAG_OUTPUT_READING  0x02

#define GBM_ONEWIRE_PRESENCE 0x13
#define GBM_ONEWIRE_PRESENCE_TAG_DEVICE_ID  0x01
#define GBM_ONEWIRE_PRESENCE_TAG_STATUS 0x02

#define GBM_AUTH_TOKEN 0x14
#define GBM_AUTH_TOKEN_TAG_DEVICE 0x01
#define GBM_AUTH_TOKEN_TAG_TOKEN 0x02
#define GBM_AUTH_TOKEN_TAG_STATUS 0x03

#define GBM_PING 0x81

#define GBM_SET_OUTPUT 0x83
#define GBM_SET_OUTPUT_TAG_OUTPUT_ID 0x01
#define GBM_SET_OUTPUT_TAG_OUTPUT_MODE 0x02

#define OUTPUT_DISABLED 0
#define OUTPUT_ENABLED 1

#define GBSP_PREFIX "GBSP v1:"
#define GBSP_PREFIX_CRC 0xe3af
#define GBSP_TRAILER "\r\n"

#define GBSP_HEADER_LEN 12
#define GBSP_HEADER_PREFIX_LEN 8
#define GBSP_HEADER_ID_LEN 2
#define GBSP_HEADER_PAYLOADLEN_LEN 2

#define GBSP_FOOTER_LEN 4
#define GBSP_FOOTER_CRC_LEN 2
#define GBSP_FOOTER_TRAILER_LEN 2

#define GBSP_PAYLOAD_MAXLEN 112

// Milliseconds/day
#define MS_PER_DAY  (1000*60*60*24)
// Interval between test pulse trains
#define GB_SELFTEST_INTERVAL_MS 500

// Number of pulses per test pulse train
#define GB_SELFTEST_PULSES 10

// Minimum time, in MS, between meter update packets. Setting this to zero will
// cause the kegboard to send a meter update message for nearly every tick; this
// is not recommended.
#define GB_METER_UPDATE_INTERVAL_MS 100
