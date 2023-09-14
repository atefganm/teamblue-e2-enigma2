installdir = $(pkgdatadir)/display/skin_default

if HAVE_TEXTLCD
DISPLAYTYPE = text
else
DISPLAYTYPE = display
endif

if HAVE_COLORLCD2
SUBDIRS = display96
endif

if HAVE_COLORLCD3
SUBDIRS = display128dm
endif

if HAVE_COLORLCD1
SUBDIRS = display128
endif

if HAVE_COLORLCD220
SUBDIRS = lcd220 lcd_skin220
endif

if HAVE_COLORLCD390
SUBDIRS = display390
endif

if HAVE_COLORLCD400
SUBDIRS = display400
endif

if HAVE_COLORLCD480
SUBDIRS = display480
endif

if HAVE_BWLCD255
SUBDIRS = vfd255
endif

dist_install_DATA = skin_display.xml

# Use box-specific XML if it exists, otherwise get the default
# TEXTSKIN is either "default" or "7segment"
# TODO: Missing dependency on optional "skin_$(DISPLAYTYPE)_$(MACHINEBUILD).xml"
skin_display.xml:
	cp $(srcdir)/skin_$(DISPLAYTYPE)_$(MACHINEBUILD).xml $@ 2>/dev/null || cp $(srcdir)/skin_$(DISPLAYTYPE)_$(TEXTSKIN).xml $@
