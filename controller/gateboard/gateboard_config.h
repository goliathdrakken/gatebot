//
// Feature configuration
//

// You may enable/disable kegboard features here as desired. The deafult are
// safe.

// Check for & report 1-wire devices on the ID bus?
#define GB_ENABLE_ONEWIRE_PRESENCE 1

// Enable buzzer?
#define GB_ENABLE_BUZZER    1

// Enable serial LCD?
#define GB_ENABLE_SERIAL_LCD 0

//
// Pin configuration
//
#define GB_PIN_DATA_0             2
#define GB_PIN_DATA_1             3
#define GB_PIN_RELAY_A            4
#define GB_PIN_RELAY_B            5
#define GB_PIN_ONEWIRE_PRESENCE   7
#define GB_PIN_ALARM              9
#define GB_PIN_BUZZER             11


#define GB_PIN_SERIAL_LCD_TX 6
#define GB_PIN_SERIAL_LCD_RX 10

//
// Device configuration defaults
//

#define GB_DEFAULT_BOARDNAME          "gateboard"
#define GB_DEFAULT_BOARDNAME_LEN      9  // must match #chars above
#define GB_DEFAULT_BAUD_RATE          115200

// Size in entries of the onewire presence bus cache.  This many IDs can be
// concurrently tracked on the bus.
#define ONEWIRE_CACHE_SIZE 8

// Number of full onewire bus searches to complete before considering a
// non-responding onewire id missing.  This is used to dampen against glitches
// where a device might be absent from a search.
#define ONEWIRE_CACHE_MAX_MISSING_SEARCHES 4
