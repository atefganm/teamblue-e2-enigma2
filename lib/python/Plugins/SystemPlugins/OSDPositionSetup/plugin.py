from Screens.Screen import Screen
from Components.config import config, ConfigSubsection, ConfigInteger
from Plugins.Plugin import PluginDescriptor

config.plugins.OSDPositionSetup = ConfigSubsection()
config.plugins.OSDPositionSetup.dst_left = ConfigInteger(default=0)
config.plugins.OSDPositionSetup.dst_width = ConfigInteger(default=720)
config.plugins.OSDPositionSetup.dst_top = ConfigInteger(default=0)
config.plugins.OSDPositionSetup.dst_height = ConfigInteger(default=576)


def setPosition(dst_left, dst_width, dst_top, dst_height):
	if dst_left + dst_width > 720:
		dst_width = 720 - dst_left
	if dst_top + dst_height > 576:
		dst_height = 576 - dst_top
	try:
		open("/proc/stb/fb/dst_left", "w").write('%08x' % dst_left)
		open("/proc/stb/fb/dst_width", "w").write('%08x' % dst_width)
		open("/proc/stb/fb/dst_top", "w").write('%08x' % dst_top)
		open("/proc/stb/fb/dst_height", "w").write('%08x' % dst_height)
	except:
		return


def setConfiguredPosition():
	setPosition(int(config.plugins.OSDPositionSetup.dst_left.value), int(config.plugins.OSDPositionSetup.dst_width.value), int(config.plugins.OSDPositionSetup.dst_top.value), int(config.plugins.OSDPositionSetup.dst_height.value))


def main(session, **kwargs):
	from .overscanwizard import OverscanWizard
	session.open(OverscanWizard, timeOut=False)


def startup(reason, **kwargs):
	setConfiguredPosition()


def OSDPosSetup(menuid, **kwargs):
	if menuid == "ui_menu":
		return [(_("Position and size"), main, "osd_position_setup", 80)]
	else:
		return []


def Plugins(**kwargs):
	return [PluginDescriptor(name=_("Overscan wizard"), description="", where=PluginDescriptor.WHERE_SESSIONSTART, fnc=startup),
		PluginDescriptor(name=_("Overscan wizard"), description=_("Wizard to arrange the overscan"), where=PluginDescriptor.WHERE_MENU, fnc=OSDPosSetup)]
