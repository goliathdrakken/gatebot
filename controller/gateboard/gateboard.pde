#include <WProgram.h>
#include <avr/pgmspace.h>
#include <string.h>
#include <util/crc16.h>
#include <util/delay.h>
#include <wiring.h>

#include "gateboard.h"
#include "gateboard_config.h"
#include "GateboardPacket.h"
#include "version.h"

#if (GB_ENABLE_ONEWIRE_PRESENCE)
#include "OneWire.h"
#endif

#if GB_ENABLE_BUZZER
#include "buzzer.h"
#endif

#if GB_ENABLE_SERIAL_LCD
#include <SoftwareSerial.h>
SoftwareSerial gSerialLcd = SoftwareSerial(GB_PIN_SERIAL_LCD_RX,
    GB_PIN_SERIAL_LCD_TX);
#endif

//
// Other Globals
//
static bool volatile gRelayStatus[] = {false, false};
static uint8_t gOutputPins[] = {GB_PIN_RELAY_A, GB_PIN_RELAY_B};

static GateboardPacket gInputPacket;

// Structure that holds the state of incoming serial bytes.
typedef struct {
  uint8_t header_bytes_read;
  uint8_t payload_bytes_remain;
  bool have_packet;
} RxPacketStat;

static RxPacketStat gPacketStat;

// Structure to keep information about this device's uptime. 
typedef struct {
  unsigned long uptime_ms;
  unsigned long last_uptime_ms;
  unsigned long last_meter_event;
  int uptime_days;
} UptimeStat;

static UptimeStat gUptimeStat;

#if GB_ENABLE_ONEWIRE_PRESENCE
// Structure used to cache information about devices on the onewire bus.
typedef struct {
  uint64_t id;
  bool valid;
  uint8_t present_count;
} OnewireEntry;

static OnewireEntry gOnewireCache[ONEWIRE_CACHE_SIZE];
#endif

#if GB_ENABLE_BUZZER
PROGMEM prog_uint16_t BOOT_MELODY[] = {
  MELODY_NOTE(4, 3, 100), MELODY_NOTE(0, NOTE_SILENCE, 100),
  MELODY_NOTE(4, 3, 70 ), MELODY_NOTE(0, NOTE_SILENCE, 25),
  MELODY_NOTE(4, 3, 100), MELODY_NOTE(0, NOTE_SILENCE, 25),

  MELODY_NOTE(4, 0, 100), MELODY_NOTE(0, NOTE_SILENCE, 25),
  MELODY_NOTE(4, 0, 100), MELODY_NOTE(0, NOTE_SILENCE, 25),
  MELODY_NOTE(4, 0, 100), MELODY_NOTE(0, NOTE_SILENCE, 25),

  MELODY_NOTE(4, 3, 100), MELODY_NOTE(0, NOTE_SILENCE, 25),
  MELODY_NOTE(4, 3, 100), MELODY_NOTE(0, NOTE_SILENCE, 25),
  MELODY_NOTE(4, 3, 100), MELODY_NOTE(0, NOTE_SILENCE, 25),
  MELODY_NOTE(4, 3, 100), MELODY_NOTE(4, 3, 100),

  MELODY_NOTE(0, NOTE_SILENCE, 0)
};
#endif

#if GB_ENABLE_ONEWIRE_PRESENCE
static OneWire gOnewireIdBus(GB_PIN_ONEWIRE_PRESENCE);
#endif

//
// ISRs
//

void DATA0()
{
  //;
}

void DATA1()
{
  //;
}

//
// Serial I/O
//

void writeHelloPacket()
{
  int foo = FIRMWARE_VERSION;
  GateboardPacket packet;
  packet.SetType(GBM_HELLO_ID);
  packet.AddTag(GBM_HELLO_TAG_FIRMWARE_VERSION, sizeof(foo), (char*)&foo);
  packet.Print();
}

void writeRelayPacket(int channel)
{
  char name[7] = "relay-";
  int status = (int)(gRelayStatus[channel]);
  name[6] = 0x30 + channel;
  GateboardPacket packet;
  packet.SetType(GBM_OUTPUT_STATUS);
  packet.AddTag(GBM_OUTPUT_STATUS_TAG_OUTPUT_NAME, 7, name);
  packet.AddTag(GBM_OUTPUT_STATUS_TAG_OUTPUT_READING, sizeof(status), (char*)(&status));
  packet.Print();
}

void writeAuthPacket(char* device_name, uint8_t* token, int token_len,
    char status) {
  GateboardPacket packet;
  packet.SetType(GBM_AUTH_TOKEN);
  packet.AddTag(GBM_AUTH_TOKEN_TAG_DEVICE, strlen(device_name), device_name);
  packet.AddTag(GBM_AUTH_TOKEN_TAG_TOKEN, token_len, (char*)token);
  packet.AddTag(GBM_AUTH_TOKEN_TAG_STATUS, 1, &status);
  packet.Print();
}

//
// Main
//

void setup()
{
  memset(&gUptimeStat, 0, sizeof(UptimeStat));
  memset(&gPacketStat, 0, sizeof(RxPacketStat));

  // Wiegand steup. Enable internal weak pullup.
  pinMode(GB_PIN_DATA_0, INPUT);
  digitalWrite(GB_PIN_DATA_0, HIGH);
  attachInterrupt(0, DATA0, RISING);

  pinMode(GB_PIN_DATA_1, INPUT);
  digitalWrite(GB_PIN_DATA_1, HIGH);
  attachInterrupt(1, DATA1, RISING);

  pinMode(GB_PIN_RELAY_A, OUTPUT);
  pinMode(GB_PIN_RELAY_B, OUTPUT);
  pinMode(GB_PIN_ALARM, OUTPUT);

  Serial.begin(115200);

#if GB_ENABLE_BUZZER
  pinMode(GB_PIN_BUZZER, OUTPUT);
  setupBuzzer();
  playMelody(BOOT_MELODY);
#endif

#if GB_ENABLE_SERIAL_LCD
  pinMode(GB_PIN_SERIAL_LCD_RX, INPUT);
  pinMode(GB_PIN_SERIAL_LCD_TX, OUTPUT);
  gSerialLcd.begin(9600);

  // Clear display
  gSerialLcd.print('\x0c');

  // Disable cursor
  gSerialLcd.print('\xfe');
  gSerialLcd.print('\x54');

  gSerialLcd.print("Kegbot!");
#endif

  writeHelloPacket();
}

void updateTimekeeping() {
  // TODO(mikey): it would be more efficient to take control of timer0
  unsigned long now = millis();
  gUptimeStat.uptime_ms += now - gUptimeStat.last_uptime_ms;
  gUptimeStat.last_uptime_ms = now;

  if (gUptimeStat.uptime_ms >= MS_PER_DAY) {
    gUptimeStat.uptime_days += 1;
    gUptimeStat.uptime_ms -= MS_PER_DAY;
  }
}

#if GB_ENABLE_ONEWIRE_PRESENCE
void stepOnewireIdBus() {
  uint64_t addr;
  uint8_t* addr_ptr = (uint8_t*) &addr;

  // No more devices on the bus; reset the bus.
  if (!gOnewireIdBus.search(addr_ptr)) {
    gOnewireIdBus.reset_search();

    for (int i=0; i < ONEWIRE_CACHE_SIZE; i++) {
      OnewireEntry* entry = &gOnewireCache[i];
      if (!entry->valid) {
        continue;
      }

      entry->present_count -= 1;
      if (entry->present_count == 0) {
        entry->valid = false;
        writeAuthPacket("onewire", (uint8_t*)&(entry->id), 8, 0);
      }
    }
    return;
  }

  // We found a device; check the address CRC and ignore if invalid.
  if (OneWire::crc8(addr_ptr, 7) != addr_ptr[7]) {
    return;
  }

  // Ignore the null address. TODO(mikey): Is there a bug in OneWire.cpp that
  // causes this to be reported?
  if (addr == 0) {
    return;
  }

  // Look for id in cache. If seen last time around, mark present (and do not
  // emit packet).
  for (int i=0; i < ONEWIRE_CACHE_SIZE; i++) {
    OnewireEntry* entry = &gOnewireCache[i];
    if (entry->valid && entry->id == addr) {
      entry->present_count = ONEWIRE_CACHE_MAX_MISSING_SEARCHES;
      return;
    }
  }

  // Add id to cache and emit presence packet.
  // NOTE(mikey): If the cache is full, no packet will be emitted. This is
  // probably the best behavior; removing a device from the bus will clear up an
  // entry in the cache.
  for (int i=0; i < ONEWIRE_CACHE_SIZE; i++) {
    OnewireEntry* entry = &gOnewireCache[i];
    if (!entry->valid) {
      entry->valid = true;
      entry->present_count = ONEWIRE_CACHE_MAX_MISSING_SEARCHES;
      entry->id = addr;
      writeAuthPacket("onewire", (uint8_t*)&(entry->id), 8, 1);
      return;
    }
  }
}
#endif

static void readSerialBytes(char *dest_buf, int num_bytes, int offset) {
  while (num_bytes-- != 0) {
    dest_buf[offset++] = Serial.read();
  }
}

void debug(const char* msg) {
#if GB_ENABLE_SERIAL_LCD
  gSerialLcd.print('\x0c');
  gSerialLcd.print(msg);
  delay(500);
#endif
}

void resetInputPacket() {
  memset(&gPacketStat, 0, sizeof(RxPacketStat));
  gInputPacket.Reset();
}

void readIncomingSerialData() {
  char serial_buf[GBSP_PAYLOAD_MAXLEN];
  volatile uint8_t bytes_available = Serial.available();

  // Do not read a new packet if we have one awiting processing.  This should
  // never happen.
  if (gPacketStat.have_packet) {
    return;
  }

  // Look for a new packet.
  if (gPacketStat.header_bytes_read < GBSP_HEADER_PREFIX_LEN) {
    while (bytes_available > 0) {
      char next_char = Serial.read();
      bytes_available -= 1;

      if (next_char == GBSP_PREFIX[gPacketStat.header_bytes_read]) {
        gPacketStat.header_bytes_read++;
        if (gPacketStat.header_bytes_read == GBSP_HEADER_PREFIX_LEN) {
          // Found start of packet, break.
          break;
        }
      } else {
        // Wrong character in prefix; reset framing.
        if (next_char == GBSP_PREFIX[0]) {
          gPacketStat.header_bytes_read = 1;
        } else {
          gPacketStat.header_bytes_read = 0;
        }
      }
    }
  }

  // Read the remainder of the header, if not yet found.
  if (gPacketStat.header_bytes_read < GBSP_HEADER_LEN) {
    if (bytes_available < 4) {
      return;
    }
    gInputPacket.SetType(Serial.read() | (Serial.read() << 8));
    gPacketStat.payload_bytes_remain = Serial.read() | (Serial.read() << 8);
    bytes_available -= 4;
    gPacketStat.header_bytes_read += 4;

    // Check that the 'len' field is not bogus. If it is, throw out the packet
    // and reset.
    if (gPacketStat.payload_bytes_remain > GBSP_PAYLOAD_MAXLEN) {
      goto out_reset;
    }
  }

  // If we haven't yet found a frame, or there are no more bytes to read after
  // finding a frame, bail out.
  if (bytes_available == 0 || (gPacketStat.header_bytes_read < GBSP_HEADER_LEN)) {
    return;
  }

  // TODO(mikey): Just read directly into GateboardPacket.
  if (gPacketStat.payload_bytes_remain) {
    int bytes_to_read = (gPacketStat.payload_bytes_remain >= bytes_available) ?
        bytes_available : gPacketStat.payload_bytes_remain;
    readSerialBytes(serial_buf, bytes_to_read, 0);
    gInputPacket.AppendBytes(serial_buf, bytes_to_read);
    gPacketStat.payload_bytes_remain -= bytes_to_read;
    bytes_available -= bytes_to_read;
  }

  // Need more payload bytes than are now available.
  if (gPacketStat.payload_bytes_remain > 0) {
    return;
  }

  // We have a complete payload. Now grab the footer.
  if (!gPacketStat.have_packet) {
    if (bytes_available < GBSP_FOOTER_LEN) {
      return;
    }
    readSerialBytes(serial_buf, GBSP_FOOTER_LEN, 0);

    // Check CRC

    // Check trailer
    if (strncmp((serial_buf + 2), GBSP_TRAILER, GBSP_FOOTER_TRAILER_LEN)) {
      goto out_reset;
    }
    gPacketStat.have_packet = true;
  }

  // Done!
  return;

out_reset:
  resetInputPacket();
}

void handleInputPacket() {
  if (!gPacketStat.have_packet) {
    return;
  }

  // Process the input packet.
  switch (gInputPacket.GetType()) {
    case GBM_PING:
      writeHelloPacket();
      break;

    case GBM_SET_OUTPUT: {
      uint8_t id, mode;
      if (!gInputPacket.ReadTag(GBM_SET_OUTPUT_TAG_OUTPUT_ID, &id)
        || !gInputPacket.ReadTag(GBM_SET_OUTPUT_TAG_OUTPUT_MODE, &mode))
        {
          break;
      }

      // TODO(mikey): bounds check id
      if (mode == OUTPUT_DISABLED) {
        digitalWrite(gOutputPins[id], LOW);
        gRelayStatus[id] = false;
      } else {
        digitalWrite(gOutputPins[id], HIGH);
        gRelayStatus[id] = true;
      }
      writeRelayPacket(id);
      break;
    }
  }
  resetInputPacket();
}

void loop()
{
  updateTimekeeping();

  readIncomingSerialData();
  handleInputPacket();

  //writeRelayPacket(0);
  //writeRelayPacket(1);

#if GB_ENABLE_ONEWIRE_PRESENCE
  stepOnewireIdBus();
#endif
}

// vim: syntax=c
