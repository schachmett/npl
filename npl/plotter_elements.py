"""Custom SpanSelector widget that has a higher rectangle without visible
up/down borders."""

import numpy as np

from matplotlib.widgets import _SelectorWidget
from matplotlib.patches import Rectangle, Wedge
from matplotlib.transforms import blended_transform_factory


class PeakSelector(_SelectorWidget):
    """Draw a Peak as triangle."""
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=invalid-name
    # pylint: disable=attribute-defined-outside-init
    def __init__(self, ax, onselect, minfwhm=None, minamp=None, useblit=False,
                 wedgeprops=None, onmove_callback=None, peak_stays=False,
                 button=None):
        _SelectorWidget.__init__(
            self, ax, onselect, useblit=useblit, button=button)

        if wedgeprops is None:
            wedgeprops = dict(facecolor='red', alpha=0.5)

        wedgeprops['animated'] = self.useblit

        self.wedge = None
        self.pressv = None

        self.wedgeprops = wedgeprops
        self.onmove_callback = onmove_callback
        self.minfwhm = minfwhm
        self.minamp = minamp
        self.peak_stays = peak_stays

        # Needed when dragging out of axes
        self.prev = (0, 0)

        # Reset canvas so that `new_axes` connects events.
        self.canvas = None
        self.new_axes(ax)

    def new_axes(self, ax):
        """Set SpanSelector to operate on a new Axes"""
        self.ax = ax
        if self.canvas is not ax.figure.canvas:
            if self.canvas is not None:
                self.disconnect_events()

            self.canvas = ax.figure.canvas
            self.connect_default_events()

        self.wedge = Wedge((0, 0), 1e10, 0, 0,
                           visible=False,
                           **self.wedgeprops)
        if self.peak_stays:
            self.stay_wedge = Wedge((0, 0), 1e10, 0, 0,
                                    visible=False,
                                    **self.wedgeprops)
            self.stay_wedge.set_animated(False)
            self.ax.add_patch(self.stay_wedge)

        self.ax.add_patch(self.wedge)
        self.artists = [self.wedge]

    def set_wedgeprops(self, wedgeprops):
        """Custom: set new rectprops."""
        self.wedgeprops = wedgeprops
        self.new_axes(self.ax)

    def ignore(self, event):
        """return *True* if *event* should be ignored"""
        return _SelectorWidget.ignore(self, event) or not self.visible

    def _press(self, event):
        """on button press event"""
        self.wedge.set_visible(self.visible)
        if self.peak_stays:
            self.stay_wedge.set_visible(False)
            # really force a draw so that the stay rect is not in
            # the blit background
            if self.useblit:
                self.canvas.draw()
        x0, y0 = self._get_data(event)
        self.pressv = (x0, y0)
        self.wedge.set_center((x0, y0))
        return False

    def _release(self, event):
        """on button release event"""
        if self.pressv is None:
            return
        self.buttonDown = False

        self.wedge.set_visible(False)

        if self.peak_stays:
            self.stay_wedge.set_center(self.wedge.center)
            self.stay_wedge.set_radius(self.wedge.r)
            self.stay_wedge.set_theta1(self.wedge.theta1)
            self.stay_wedge.set_theta2(self.wedge.theta2)
            self.stay_wedge.set_visible(True)

        self.canvas.draw_idle()

        x0, y0, = self.pressv
        center = x0
        amplitude = y0

        x, y = self._get_data(event)
        angle = abs(np.rad2deg(np.arctan((x - x0) / (y - y0))))

        # TODO: control minamp, minfwhm stuff

        self.onselect(center, amplitude, angle)
        self.pressv = None
        return False

    def _onmove(self, event):
        """on motion notify event"""
        if self.pressv is None:
            return
        x, y = self._get_data(event)
        if x is None:
            return
        x0, y0, = self.pressv

        angle = abs(np.rad2deg(np.arctan((x - x0) / (y - y0))))
        self.wedge.set_theta1(-angle - 90)
        self.wedge.set_theta2(angle - 90)

        if self.onmove_callback is not None:
            center = x0
            amplitude = y0
            self.onmove_callback(center, amplitude, angle)

        self.update()
        return False


class SpanSelector(_SelectorWidget):
    """Custom SpanSelector."""
    # pylint: disable=too-many-instance-attributes
    # pylint: disable=too-many-arguments
    # pylint: disable=attribute-defined-outside-init
    # pylint: disable=invalid-name
    def __init__(self, ax, onselect, direction, minspan=None, useblit=False,
                 rectprops=None, onmove_callback=None, span_stays=False,
                 button=None):

        _SelectorWidget.__init__(self, ax, onselect, useblit=useblit,
                                 button=button)

        if rectprops is None:
            rectprops = dict(facecolor='red', alpha=0.5)

        rectprops['animated'] = self.useblit

        if direction not in ['horizontal', 'vertical']:
            msg = "direction must be in [ 'horizontal' | 'vertical' ]"
            raise ValueError(msg)
        self.direction = direction

        self.rect = None
        self.pressv = None

        self.rectprops = rectprops
        self.onmove_callback = onmove_callback
        self.minspan = minspan
        self.span_stays = span_stays

        # Needed when dragging out of axes
        self.prev = (0, 0)

        # Reset canvas so that `new_axes` connects events.
        self.canvas = None
        self.new_axes(ax)

    def new_axes(self, ax):
        """Set SpanSelector to operate on a new Axes"""
        self.ax = ax
        if self.canvas is not ax.figure.canvas:
            if self.canvas is not None:
                self.disconnect_events()

            self.canvas = ax.figure.canvas
            self.connect_default_events()

        if self.direction == 'horizontal':
            trans = blended_transform_factory(self.ax.transData,
                                              self.ax.transAxes)
            w, h = 0, 1.5
        else:
            trans = blended_transform_factory(self.ax.transAxes,
                                              self.ax.transData)
            w, h = 1, 0
        self.rect = Rectangle((0, -0.5), w, h,
                              transform=trans,
                              visible=False,
                              **self.rectprops)
        if self.span_stays:
            self.stay_rect = Rectangle((0, 0), w, h,
                                       transform=trans,
                                       visible=False,
                                       **self.rectprops)
            self.stay_rect.set_animated(False)
            self.ax.add_patch(self.stay_rect)

        self.ax.add_patch(self.rect)
        self.artists = [self.rect]

    def set_rectprops(self, rectprops):
        """Custom: set new rectprops."""
        self.rectprops = rectprops
        self.new_axes(self.ax)

    def ignore(self, event):
        """return *True* if *event* should be ignored"""
        return _SelectorWidget.ignore(self, event) or not self.visible

    def _press(self, event):
        """on button press event"""
        self.rect.set_visible(self.visible)
        if self.span_stays:
            self.stay_rect.set_visible(False)
            # really force a draw so that the stay rect is not in
            # the blit background
            if self.useblit:
                self.canvas.draw()
        xdata, ydata = self._get_data(event)
        if self.direction == 'horizontal':
            self.pressv = xdata
        else:
            self.pressv = ydata
        return False

    def _release(self, event):
        """on button release event"""
        if self.pressv is None:
            return
        self.buttonDown = False

        self.rect.set_visible(False)

        if self.span_stays:
            self.stay_rect.set_x(self.rect.get_x())
            self.stay_rect.set_y(self.rect.get_y())
            self.stay_rect.set_width(self.rect.get_width())
            self.stay_rect.set_height(self.rect.get_height())
            self.stay_rect.set_visible(True)

        self.canvas.draw_idle()
        vmin = self.pressv
        xdata, ydata = self._get_data(event)
        if self.direction == 'horizontal':
            vmax = xdata or self.prev[0]
        else:
            vmax = ydata or self.prev[1]

        if vmin > vmax:
            vmin, vmax = vmax, vmin
        span = vmax - vmin
        if self.minspan is not None and span < self.minspan:
            return
        self.onselect(vmin, vmax)
        self.pressv = None
        return False

    def _onmove(self, event):
        """on motion notify event"""
        if self.pressv is None:
            return
        x, y = self._get_data(event)
        if x is None:
            return

        self.prev = x, y
        if self.direction == 'horizontal':
            v = x
        else:
            v = y

        minv, maxv = v, self.pressv
        if minv > maxv:
            minv, maxv = maxv, minv
        if self.direction == 'horizontal':
            self.rect.set_x(minv)
            self.rect.set_width(maxv - minv)
        else:
            self.rect.set_y(minv)
            self.rect.set_height(maxv - minv)

        if self.onmove_callback is not None:
            vmin = self.pressv
            xdata, ydata = self._get_data(event)
            if self.direction == 'horizontal':
                vmax = xdata or self.prev[0]
            else:
                vmax = ydata or self.prev[1]

            if vmin > vmax:
                vmin, vmax = vmax, vmin
            self.onmove_callback(vmin, vmax)

        self.update()
        return False


class DraggableVLine():
    """A draggable vertical line in the plot."""
    lock = None
    def __init__(self, line):
        self.line = line
        self.press = None
        self.background = None

        self.connect()

    def change_line(self, line):
        """Gets another line to drag."""
        self.disconnect()
        self.line = line
        self.connect()

    def connect(self):
        """Connect to the signals."""
        self.cidpress = self.line.figure.canvas.mpl_connect(
            "button_press_event", self.on_press)
        self.cidrelease = self.line.figure.canvas.mpl_connect(
            "button_release_event", self.on_release)
        self.cidmotion = self.line.figure.canvas.mpl_connect(
            "motion_notify_event", self.on_motion)

    def disconnect(self):
        """Disconnects from canvas signals."""
        self.line.figure.canvas.mpl_disconnect(self.cidpress)
        self.line.figure.canvas.mpl_disconnect(self.cidrelease)
        self.line.figure.canvas.mpl_disconnect(self.cidmotion)

    def on_press(self, event):
        """When the mouse button is pressed."""
        if event.inaxes != self.line.axes:
            return
        if self.lock is not None:
            return
        if not self.line.contains(event)[0]:
            return

        self.press = self.line.get_xdata(), event.xdata, event.ydata
        self.lock = self

        self.line.set_animated(True)
        self.line.figure.canvas.draw()
        self.background = self.line.figure.canvas.copy_from_bbox(
            self.line.axes.bbox)
        self.line.axes.draw_artist(self.line)
        self.line.figure.canvas.blit(self.line.axes.bbox)

    def on_release(self, _event):
        """When the mouse button is released."""
        if self.lock is not self:
            return

        self.press = None
        self.lock = None

        self.line.set_animated(False)
        self.background = None
        self.line.figure.canvas.draw()

    def on_motion(self, event):
        """When the mouse is moved in pressed state."""
        if self.lock is not self:
            return
        if event.inaxes != self.line.axes:
            return

        xdata, xpress, _ = self.press
        self.line.set_xdata(xdata)
        xdiff = event.xdata - xpress
        self.line.set_xdata([self.line.get_xdata()[0] + xdiff] * 2)

        self.line.figure.canvas.restore_region(self.background)
        self.line.axes.draw_artist(self.line)
        self.line.figure.canvas.blit(self.line.axes.bbox)
