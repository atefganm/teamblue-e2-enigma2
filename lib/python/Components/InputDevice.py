from Components.SystemInfo import BoxInfo
from fcntl import ioctl
import os
import struct

from Components.config import config, ConfigSubsection, ConfigInteger, ConfigYesNo, ConfigText, ConfigSlider
from Tools.Directories import pathExists
import platform

# include/uapi/asm-generic/ioctl.h
IOC_NRBITS = 8
IOC_TYPEBITS = 8
IOC_SIZEBITS = 13 if "mips" in platform.machine() else 14
IOC_DIRBITS = 3 if "mips" in platform.machine() else 2

IOC_NRSHIFT = 0
IOC_TYPESHIFT = IOC_NRSHIFT + IOC_NRBITS
IOC_SIZESHIFT = IOC_TYPESHIFT + IOC_TYPEBITS
IOC_DIRSHIFT = IOC_SIZESHIFT + IOC_SIZEBITS

IOC_READ = 2


def EVIOCGNAME(length):
	return (IOC_READ << IOC_DIRSHIFT) | (length << IOC_SIZESHIFT) | (0x45 << IOC_TYPESHIFT) | (0x06 << IOC_NRSHIFT)


class inputDevices:

	def __init__(self):
		self.Devices = {}
		self.currentDevice = ""
		self.getInputDevices()

	def getInputDevices(self):
		devices = sorted(os.listdir("/dev/input/"))

		for evdev in devices:
			try:
				buffer = "\0" * 512
				self.fd = os.open("/dev/input/" + evdev, os.O_RDWR | os.O_NONBLOCK)
				self.name = ioctl(self.fd, EVIOCGNAME(256), buffer).decode()
				self.name = self.name[:self.name.find("\0")]
				if str(self.name).find("Keyboard") != -1:
					self.name = 'keyboard'
				os.close(self.fd)
			except (IOError, OSError) as err:
				print("[InputDevice] getInputDevices " + evdev + " <ERROR: ioctl(EVIOCGNAME): " + str(err) + " >")
				self.name = None

			if self.name:
				self.Devices[evdev] = {'name': self.name, 'type': self.getInputDeviceType(self.name), 'enabled': False, 'configuredName': None}

	def getInputDeviceType(self, name):
		if "remote control" in str(name).lower():
			return "remote"
		elif "keyboard" in str(name).lower():
			return "keyboard"
		elif "mouse" in str(name).lower():
			return "mouse"
		else:
			print("[InputDevice] Unknown device type:", name)
			return None

	def getDeviceName(self, x):
		if x in self.Devices.keys():
			return self.Devices[x].get("name", x)
		else:
			return "Unknown device name"

	def getDeviceList(self):
		return sorted(self.Devices.keys())

	def setDeviceAttribute(self, device, attribute, value):
		#print "[InputDevice] setting for device", device, "attribute", attribute, " to value", value
		if device in self.Devices:
			self.Devices[device][attribute] = value

	def getDeviceAttribute(self, device, attribute):
		if device in self.Devices:
			if attribute in self.Devices[device]:
				return self.Devices[device][attribute]
		return None

	def setEnabled(self, device, value):
		oldval = self.getDeviceAttribute(device, 'enabled')
		#print "[InputDevice] setEnabled for device %s to %s from %s" % (device,value,oldval)
		self.setDeviceAttribute(device, 'enabled', value)
		if oldval and not value:
			self.setDefaults(device)

	def setName(self, device, value):
		#print "[InputDevice] setName for device %s to %s" % (device,value)
		self.setDeviceAttribute(device, 'configuredName', value)

	#struct input_event {
	#	struct timeval time;    -> ignored
	#	__u16 type;             -> EV_REP (0x14)
	#	__u16 code;             -> REP_DELAY (0x00) or REP_PERIOD (0x01)
	#	__s32 value;            -> DEFAULTS: 700(REP_DELAY) or 100(REP_PERIOD)
	#}; -> size = 16

	def setDefaults(self, device):
		print("[InputDevice] setDefaults for device %s" % device)
		self.setDeviceAttribute(device, 'configuredName', None)
		event_repeat = struct.pack('LLHHi', 0, 0, 0x14, 0x01, 100)
		event_delay = struct.pack('LLHHi', 0, 0, 0x14, 0x00, 700)
		fd = os.open("/dev/input/" + device, os.O_RDWR)
		os.write(fd, event_repeat)
		os.write(fd, event_delay)
		os.close(fd)

	def setRepeat(self, device, value): #REP_PERIOD
		if self.getDeviceAttribute(device, 'enabled'):
			print("[InputDevice] setRepeat for device %s to %d ms" % (device, value))
			event = struct.pack('LLHHi', 0, 0, 0x14, 0x01, int(value))
			fd = os.open("/dev/input/" + device, os.O_RDWR)
			os.write(fd, event)
			os.close(fd)

	def setDelay(self, device, value): #REP_DELAY
		if self.getDeviceAttribute(device, 'enabled'):
			print("[InputDevice] setDelay for device %s to %d ms" % (device, value))
			event = struct.pack('LLHHi', 0, 0, 0x14, 0x00, int(value))
			fd = os.open("/dev/input/" + device, os.O_RDWR)
			os.write(fd, event)
			os.close(fd)


class InitInputDevices:

	def __init__(self):
		self.currentDevice = ""
		self.createConfig()

	def createConfig(self, *args):
		config.inputDevices = ConfigSubsection()
		for device in sorted(iInputDevices.Devices.keys()):
			self.currentDevice = device
			#print "[InputDevice] creating config entry for device: %s -> %s  " % (self.currentDevice, iInputDevices.Devices[device]["name"])
			self.setupConfigEntries(self.currentDevice)
			self.currentDevice = ""

	def inputDevicesEnabledChanged(self, configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setEnabled(self.currentDevice, configElement.value)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setEnabled(iInputDevices.currentDevice, configElement.value)

	def inputDevicesNameChanged(self, configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setName(self.currentDevice, configElement.value)
			if configElement.value != "":
				devname = iInputDevices.getDeviceAttribute(self.currentDevice, 'name')
				if devname != configElement.value:
					cmd = "config.inputDevices." + self.currentDevice + ".enabled.value = False"
					exec(cmd)
					cmd = "config.inputDevices." + self.currentDevice + ".enabled.save()"
					exec(cmd)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setName(iInputDevices.currentDevice, configElement.value)

	def inputDevicesRepeatChanged(self, configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setRepeat(self.currentDevice, configElement.value)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setRepeat(iInputDevices.currentDevice, configElement.value)

	def inputDevicesDelayChanged(self, configElement):
		if self.currentDevice != "" and iInputDevices.currentDevice == "":
			iInputDevices.setDelay(self.currentDevice, configElement.value)
		elif iInputDevices.currentDevice != "":
			iInputDevices.setDelay(iInputDevices.currentDevice, configElement.value)

	def setupConfigEntries(self, device):
		cmd = "config.inputDevices." + device + " = ConfigSubsection()"
		exec(cmd)
		cmd = "config.inputDevices." + device + ".enabled = ConfigYesNo(default = False)"
		exec(cmd)
		cmd = "config.inputDevices." + device + ".enabled.addNotifier(self.inputDevicesEnabledChanged,config.inputDevices." + device + ".enabled)"
		exec(cmd)
		cmd = "config.inputDevices." + device + '.name = ConfigText(default="")'
		exec(cmd)
		cmd = "config.inputDevices." + device + ".name.addNotifier(self.inputDevicesNameChanged,config.inputDevices." + device + ".name)"
		exec(cmd)
		cmd = "config.inputDevices." + device + ".repeat = ConfigSlider(default=100, increment = 10, limits=(0, 500))"
		exec(cmd)
		cmd = "config.inputDevices." + device + ".repeat.addNotifier(self.inputDevicesRepeatChanged,config.inputDevices." + device + ".repeat)"
		exec(cmd)
		cmd = "config.inputDevices." + device + ".delay = ConfigSlider(default=700, increment = 100, limits=(0, 5000))"
		exec(cmd)
		cmd = "config.inputDevices." + device + ".delay.addNotifier(self.inputDevicesDelayChanged,config.inputDevices." + device + ".delay)"
		exec(cmd)


iInputDevices = inputDevices()


config.plugins.remotecontroltype = ConfigSubsection()
config.plugins.remotecontroltype.rctype = ConfigInteger(default=0)


class RcTypeControl:
	def __init__(self):
		if BoxInfo.getItem("RcTypeChangable") and pathExists('/proc/stb/info/boxtype'):
			self.isSupported = True
			self.boxType = open('/proc/stb/info/boxtype', 'r').read().strip()
			if config.plugins.remotecontroltype.rctype.value != 0:
				self.writeRcType(config.plugins.remotecontroltype.rctype.value)
		else:
			self.isSupported = False

	def multipleRcSupported(self):
		return self.isSupported

	def getBoxType(self):
		return self.boxType

	def writeRcType(self, rctype):
		if self.isSupported and rctype > 0:
			open('/proc/stb/ir/rc/type', 'w').write('%d' % rctype)

	def readRcType(self):
		rc = 0
		if self.isSupported:
			rc = open('/proc/stb/ir/rc/type', 'r').read().strip()
		return int(rc)


iRcTypeControl = RcTypeControl()
