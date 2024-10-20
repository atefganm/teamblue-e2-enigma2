#ifndef __lib_gui_eslider_h
#define __lib_gui_eslider_h

#include <lib/gui/ewidget.h>

class eSlider: public eWidget
{
public:
	eSlider(eWidget *parent);
	void setValue(int val);
	void setStartEnd(int start, int end);
	void setRange(int min, int max);
	enum { orHorizontal, orVertical };
	void setOrientation(int orientation, int swapped = 0);
	void setBorderWidth(int pixel);
	void setBorderColor(const gRGB &color);
	void setForegroundColor(const gRGB &color);
	void setBackgroundColor(const gRGB &col) override;
	void setPixmap(gPixmap *pixmap);
	void setPixmap(ePtr<gPixmap> &pixmap);
	void setBackgroundPixmap(gPixmap *pixmap);
	void setBackgroundPixmap(ePtr<gPixmap> &pixmap);
	void setAlphatest(int alphatest);
	void setSliderBorderWidth(int pixel);
	void setSliderBorderColor(const gRGB &color);
	void setSliderForegroundColor(const gRGB &color);
	void setScrollbarSliderPicture(gPixmap *pixmap);
	void setScrollbarSliderPicture(ePtr<gPixmap> &pixmap);
	void setScrollbarBackgroundPicture(gPixmap *pixmap);
	void setScrollbarBackgroundPicture(ePtr<gPixmap> &pixmap);
protected:
	int event(int event, void *data=0, void *data2=0);
private:
	enum eSliderEvent
	{
		evtChangedSlider = evtUserWidget
	};
	bool m_have_border_color, m_have_foreground_color, m_have_background_color;
	bool m_have_sliderborder_color, m_have_sliderforeground_color, m_have_sliderborder_width;
	int m_min, m_max, m_value, m_start, m_orientation, m_orientation_swapped, m_border_width, m_sliderborder_width;
	ePtr<gPixmap> m_pixmap, m_backgroundpixmap;
	ePtr<gPixmap> m_scrollbarslidepixmap, m_scrollbarslidebackgroundpixmap;

	gRegion m_currently_filled;
	gRGB m_border_color, m_foreground_color, m_background_color;
	gRGB m_sliderborder_color, m_sliderforeground_color;
};

#endif
