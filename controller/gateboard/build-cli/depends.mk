build-cli/buzzer.o: buzzer.cpp \
  /usr/local/arduino/hardware/arduino/cores/arduino/WConstants.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/wiring.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/binary.h buzzer.h
build-cli/GateboardPacket.o: GateboardPacket.cpp \
  /usr/local/arduino/hardware/arduino/cores/arduino/WProgram.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/wiring.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/binary.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/WCharacter.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/WString.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/HardwareSerial.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/Stream.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/Print.h gateboard.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/HardwareSerial.h \
  GateboardPacket.h
build-cli/OneWire.o: OneWire.cpp OneWire.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/WConstants.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/wiring.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/binary.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/pins_arduino.h
build-cli/gateboard.o: build-cli/gateboard.cpp \
  /usr/local/arduino/hardware/arduino/cores/arduino/WProgram.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/wiring.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/binary.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/WCharacter.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/WString.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/HardwareSerial.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/Stream.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/Print.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/wiring.h gateboard.h \
  /usr/local/arduino/hardware/arduino/cores/arduino/HardwareSerial.h \
  gateboard_config.h GateboardPacket.h version.h OneWire.h buzzer.h
