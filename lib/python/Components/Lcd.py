from __future__ import division
from Components.config import config, ConfigSubsection, ConfigSlider, ConfigYesNo, ConfigNothing, ConfigSelection
from enigma import eDBoxLCD, eActionMap
from Components.SystemInfo import SystemInfo
from Tools.Directories import fileExists
from Screens.InfoBar import InfoBar
from Screens.Screen import Screen
from sys import maxsize

from boxbranding import getBoxType


class dummyScreen(Screen):
	skin = """<screen position="0,0" size="0,0" transparent="1">
	<widget source="session.VideoPicture" render="Pig" position="0,0" size="0,0" backgroundColor="transparent" zPosition="1"/>
	</screen>"""

	def __init__(self, session, args=None):
		Screen.__init__(self, session)
		self.close()


class LCD:
	def __init__(self):
		eActionMap.getInstance().bindAction("", -maxsize - 1, self.DimUpEvent)
		self.autoDimDownLCDTimer = eTimer()
		self.autoDimDownLCDTimer.callback.append(self.autoDimDownLCD)
		self.autoDimUpLCDTimer = eTimer()
		self.autoDimUpLCDTimer.callback.append(self.autoDimUpLCD)

		self.currBrightness = self.dimBrightness = self.Brightness = None
		self.dimDelay = 10

	def DimUpEvent(self, key, flag):
		self.autoDimDownLCDTimer.stop()
		if self.Brightness is not None and not self.autoDimUpLCDTimer.isActive():
			self.autoDimUpLCDTimer.start(1)

	def autoDimDownLCD(self):
		if self.dimBrightness is not None and  self.currBrightness > self.dimBrightness:
			self.autoDimDownLCDTimer.start(10, True)
			self.currBrightness = self.currBrightness - 1
			eDBoxLCD.getInstance().setLCDBrightness(self.currBrightness)

	def autoDimUpLCD(self):
		if self.currBrightness < self.Brightness:
			self.currBrightness = self.currBrightness + 1
			eDBoxLCD.getInstance().setLCDBrightness(self.currBrightness)
		else:
			self.autoDimUpLCDTimer.stop()
			if self.dimBrightness is not None and  self.currBrightness > self.dimBrightness:
				if self.dimDelay is not None and self.dimDelay > 0:
					self.autoDimDownLCDTimer.startLongTimer(self.dimDelay)

	def setBright(self, value):
		value *= 255
		value //= 10
		if value > 255:
			value = 255
		self.Brightness = value
		self.DimUpEvent(None, None)

	def setStandbyBright(self, value):
		value *= 255
		value //= 10
		if value > 255:
			value = 255
		self.autoDimDownLCDTimer.stop()
		self.autoDimUpLCDTimer.stop()
		self.Brightness = value
		if self.dimBrightness is None:
			self.dimBrightness = value
		if self.currBrightness is None:
			self.currBrightness = value
		self.autoDimDownLCD()

	def setDimBright(self, value):
		value *= 255
		value //= 10
		if value > 255:
			value = 255
		self.dimBrightness = value

	def setDimDelay(self, value):
		self.dimDelay = int(value)

	def setContrast(self, value):
		value *= 63
		value //= 20
		if value > 63:
			value = 63
		eDBoxLCD.getInstance().setLCDContrast(value)

	def setInverted(self, value):
		if value:
			value = 255
		eDBoxLCD.getInstance().setInverted(value)

	def setFlipped(self, value):
		eDBoxLCD.getInstance().setFlipped(value)

	def setScreenShot(self, value):
		eDBoxLCD.getInstance().setDump(value)

	def isOled(self):
		return eDBoxLCD.getInstance().isOled()


def leaveStandby():
	config.lcd.bright.apply()


def standbyCounterChanged(dummy):
	from Screens.Standby import inStandby
	inStandby.onClose.append(leaveStandby)
	config.lcd.standby.apply()


def InitLcd():
	if getBoxType() in ('gb800se', 'gb800solo', 'gb800seplus', 'gbipbox', 'gbultra', 'gbultrase', 'spycat', 'quadbox2400', 'gbx1', 'gbx2', 'gbx3', 'gbx3h', 'gbx34k'):
		detected = False
	else:
		detected = eDBoxLCD.getInstance() and eDBoxLCD.getInstance().detected()

	SystemInfo["Display"] = detected
	config.lcd = ConfigSubsection()

	if fileExists("/proc/stb/lcd/mode"):
		f = open("/proc/stb/lcd/mode", "r")
		can_lcdmodechecking = f.read().strip().split(" ")
		f.close()
	else:
		can_lcdmodechecking = False

	SystemInfo["LCDMiniTV"] = can_lcdmodechecking

	if detected:
		ilcd = LCD()
		if can_lcdmodechecking:
			def setLCDModeMinitTV(configElement):
				try:
					f = open("/proc/stb/lcd/mode", "w")
					f.write(configElement.value)
					f.close()
				except:
					pass

			def setMiniTVFPS(configElement):
				try:
					f = open("/proc/stb/lcd/fps", "w")
					f.write("%d \n" % configElement.value)
					f.close()
				except:
					pass

			def setLCDModePiP(configElement):
				pass  # DEBUG: Should this be doing something?

			config.lcd.modepip = ConfigSelection(choices={
				"0": _("Off"),
				"5": _("PiP"),
				"7": _("PiP with OSD")
			}, default="0")
			config.lcd.modepip.addNotifier(setLCDModePiP)
			config.lcd.modeminitv = ConfigSelection(choices={
				"0": _("normal"),
				"1": _("MiniTV"),
				"2": _("OSD"),
				"3": _("MiniTV with OSD")
			}, default="0")
			config.lcd.fpsminitv = ConfigSlider(default=30, limits=(0, 30))
			config.lcd.modeminitv.addNotifier(setLCDModeMinitTV)
			config.lcd.fpsminitv.addNotifier(setMiniTVFPS)
		else:
			config.lcd.modeminitv = ConfigNothing()
			config.lcd.screenshot = ConfigNothing()
			config.lcd.fpsminitv = ConfigNothing()
		config.lcd.scroll_speed = ConfigSelection(choices=[
			("500", _("slow")),
			("300", _("normal")),
			("100", _("fast"))
		], default="300")
		config.lcd.scroll_delay = ConfigSelection(choices=[
			("10000", "10 %s" % _("Seconds")),
			("20000", "20 %s" % _("Seconds")),
			("30000", "30 %s" % _("Seconds")),
			("60000", "1 %s" % _("Minute")),
			("300000", "5 %s" % _("Minutes")),
			("noscrolling", _("Off"))
		], default="10000")

		def setLCDbright(configElement):
			ilcd.setBright(configElement.value)

		def setLCDstandbybright(configElement):
			ilcd.setStandbyBright(configElement.value);

		def setLCDdimbright(configElement):
			ilcd.setDimBright(configElement.value);

		def setLCDdimdelay(configElement):
			ilcd.setDimDelay(configElement.value);

		def setLCDcontrast(configElement):
			ilcd.setContrast(configElement.value)

		def setLCDinverted(configElement):
			ilcd.setInverted(configElement.value)

		def setLCDflipped(configElement):
			ilcd.setFlipped(configElement.value)

		def setLedPowerColor(configElement):
			if fileExists("/proc/stb/fp/ledpowercolor"):
				f = open("/proc/stb/fp/ledpowercolor", "w")
				f.write(configElement.value)
				f.close()

		def setLedStandbyColor(configElement):
			if fileExists("/proc/stb/fp/ledstandbycolor"):
				f = open("/proc/stb/fp/ledstandbycolor", "w")
				f.write(configElement.value)
				f.close()

		def setLedSuspendColor(configElement):
			if fileExists("/proc/stb/fp/ledsuspendledcolor"):
				f = open("/proc/stb/fp/ledsuspendledcolor", "w")
				f.write(configElement.value)
				f.close()

		def setPower4x7On(configElement):
			if fileExists("/proc/stb/fp/power4x7on"):
				f = open("/proc/stb/fp/power4x7on", "w")
				f.write(configElement.value)
				f.close()

		def setPower4x7Standby(configElement):
			if fileExists("/proc/stb/fp/power4x7standby"):
				f = open("/proc/stb/fp/power4x7standby", "w")
				f.write(configElement.value)
				f.close()

		def setPower4x7Suspend(configElement):
			if fileExists("/proc/stb/fp/power4x7suspend"):
				f = open("/proc/stb/fp/power4x7suspend", "w")
				f.write(configElement.value)
				f.close()

		standby_default = 0

		ilcd = LCD()

		if not ilcd.isOled():
			config.lcd.contrast = ConfigSlider(default=5, limits=(0, 20))
			config.lcd.contrast.addNotifier(setLCDcontrast)
		else:
			config.lcd.contrast = ConfigNothing()

		config.usage.lcd_ledpowercolor = ConfigSelection(default = "1", choices = [("0", _("off")),("1", _("blue")), ("2", _("red")), ("3", _("violet"))])
		config.usage.lcd_ledpowercolor.addNotifier(setLedPowerColor)

		config.usage.lcd_ledstandbycolor = ConfigSelection(default = "3", choices = [("0", _("off")),("1", _("blue")), ("2", _("red")), ("3", _("violet"))])
		config.usage.lcd_ledstandbycolor.addNotifier(setLedStandbyColor)

		config.usage.lcd_ledsuspendcolor = ConfigSelection(default = "2", choices = [("0", _("off")),("1", _("blue")), ("2", _("red")), ("3", _("violet"))])
		config.usage.lcd_ledsuspendcolor.addNotifier(setLedSuspendColor)

		config.usage.lcd_power4x7on = ConfigSelection(default = "on", choices = [("off", _("Off")), ("on", _("On"))])
		config.usage.lcd_power4x7on.addNotifier(setPower4x7On)

		config.usage.lcd_power4x7standby = ConfigSelection(default = "off", choices = [("off", _("Off")), ("on", _("On"))])
		config.usage.lcd_power4x7standby.addNotifier(setPower4x7Standby)

		config.usage.lcd_power4x7suspend = ConfigSelection(default = "off", choices = [("off", _("Off")), ("on", _("On"))])
		config.usage.lcd_power4x7suspend.addNotifier(setPower4x7Suspend)

			if getBoxType() in ('dm900','dm920'):
				standby_default = 4
			else:
				standby_default = 1

		config.lcd.standby = ConfigSlider(default=standby_default, limits=(0, 10))
		config.lcd.standby.addNotifier(setLCDbright)
		config.lcd.dimbright = ConfigSlider(default=standby_default, limits=(0, 4))
		config.lcd.standby.apply = lambda: setLCDbright(config.lcd.standby)
		config.lcd.dimbright = ConfigSlider(default=standby_default, limits=(0, 10))
		config.lcd.bright = ConfigSlider(default=5, limits=(0, 10))
		config.lcd.dimbright.addNotifier(setLCDdimbright);
		config.lcd.dimbright.apply = lambda : setLCDdimbright(config.lcd.dimbright)
		config.lcd.dimdelay.addNotifier(setLCDdimdelay);
		config.lcd.standby.addNotifier(setLCDstandbybright);
		config.lcd.standby.apply = lambda : setLCDstandbybright(config.lcd.standby)
		config.lcd.bright.addNotifier(setLCDbright)
		config.lcd.bright.apply = lambda: setLCDbright(config.lcd.bright)
		config.lcd.bright.callNotifiersOnSaveAndCancel = True
		config.lcd.invert = ConfigYesNo(default=False)
		config.lcd.invert.addNotifier(setLCDinverted)
		config.lcd.flip = ConfigYesNo(default=False)
		config.lcd.flip.addNotifier(setLCDflipped)

		if SystemInfo["LcdLiveTV"]:
			def lcdLiveTvChanged(configElement):
				setLCDLiveTv(configElement.value)
				configElement.save()
			config.lcd.showTv = ConfigYesNo(default=False)
			config.lcd.showTv.addNotifier(lcdLiveTvChanged)

			if "live_enable" in SystemInfo["LcdLiveTV"]:
				config.misc.standbyCounter.addNotifier(standbyCounterChangedLCDLiveTV, initial_call=False)
	else:
		def doNothing():
			pass
		config.lcd.contrast = ConfigNothing()
		config.lcd.bright = ConfigNothing()
		config.lcd.standby = ConfigNothing()
		config.lcd.bright.apply = lambda: doNothing()
		config.lcd.standby.apply = lambda: doNothing()

	config.misc.standbyCounter.addNotifier(standbyCounterChanged, initial_call=False)


def setLCDLiveTv(value):
	if "live_enable" in SystemInfo["LcdLiveTV"]:
		open(SystemInfo["LcdLiveTV"], "w").write(value and "enable" or "disable")
	else:
		open(SystemInfo["LcdLiveTV"], "w").write(value and "0" or "1")
	if not value:
		try:
			InfoBarInstance = InfoBar.instance
			InfoBarInstance and InfoBarInstance.session.open(dummyScreen)
		except:
			pass


def leaveStandbyLCDLiveTV():
	if config.lcd.showTv.value:
		setLCDLiveTv(True)


def standbyCounterChangedLCDLiveTV(dummy):
	if config.lcd.showTv.value:
		from Screens.Standby import inStandby
		if leaveStandbyLCDLiveTV not in inStandby.onClose:
			inStandby.onClose.append(leaveStandbyLCDLiveTV)
		setLCDLiveTv(False)
