# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © SARDES Project Contributors
# https://github.com/cgq-qgc/sardes
#
# This file is part of SARDES.
# Licensed under the terms of the GNU General Public License.
# -----------------------------------------------------------------------------

# ---- Standard library imports
import os.path as osp

# ---- Third party library imports
import pandas as pd
import numpy as np
from matplotlib.transforms import ScaledTranslation
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

# ---- Local imports
from sardes.config.gui import RED, BLUE
from sardes.config.locale import _
from sardes.config.main import CONF
from sardes.api.tools import SardesTool
from sardes.api.figures import SardesFigureWidget, SardesFigureCanvas


class NetworkBarchartTool(SardesTool):
    """
    A tool to produce hydrograph figures for publishing from reading data.
    """

    def __init__(self, parent):
        super().__init__(
            parent,
            name='network_barchart_tool',
            text=_("Network Portrait"),
            icon='chart_pie',
            tip=_("Create charts.")
            )

    # ---- SardesTool API
    def __update_toolwidget__(self, toolwidget):
        table_model = self.parent.model()
        toolwidget.canvas.figure.plot_barchart(
            table_model.libraries['observation_wells_data_overview'],
            table_model.dataf)

    def __create_toolwidget__(self):
        return NetworkBarchartWidget()


class NetworkBarchartWidget(SardesFigureWidget):
    def __init__(self):
        canvas = NetworkBarchartCanvas(parent=self)
        super().__init__(canvas)


class NetworkBarchartCanvas(SardesFigureCanvas):

    def __init__(self, figsize=(6.5, 4), parent=None):
        figure = NetworkBarchartFigure(
            figsize=figsize, facecolor='white')
        super().__init__(figure, parent)


class NetworkBarchartFigure(Figure):
    # https://chartio.com/learn/charts/bar-chart-complete-guide/

    def __init__(self, *args, **kargs):
        super().__init__(*args, **kargs)
        self.set_tight_layout(True)
        self.xlabelpad = 10
        self.ylabelpad = 10
        self.figborderpad = 15
        self.gridlinewidth = 0.75
        self.labelfontsize = 14

        self._data = pd.DataFrame([], dtype='object')
        self._total_values = ()
        self._active_values = ()
        self._inactive_values = ()

        self._active_values_annotations = ()
        self._inactive_values_annotations = ()
        self._total_values_annotations = ()
        self._active_bar_container = None
        self._inactive_bar_container = None
        self._total_bar_container = None

        self.setup_axes()
        self.setup_legend()

    def set_size_inches(self, *args, **kargs):
        """
        Override matplotlib method to force a call to tight_layout when
        set_size_inches is called. This allow to keep the size of the margins
        fixed when the canvas of this figure is resized.
        """
        super().set_size_inches(*args, **kargs)
        self.tight_layout()

    def tight_layout(self, *args, **kargs):
        """
        Override matplotlib method to setup the margins of the axes.
        """
        if len(self.axes) == 0:
            return
        try:
            # This is required when saving the figure in some format like
            # pdf and svg.
            renderer = self.canvas.get_renderer()
        except AttributeError:
            self.canvas.draw()
            return

        figborderpad = self.figborderpad/72 * self.dpi
        ylabelpad = self.ylabelpad/72 * self.dpi
        xlabelpad = self.xlabelpad/72 * self.dpi

        figbbox = self.bbox
        ax = self.axes[0]
        axbbox = ax.bbox

        bbox_xaxis_bottom, bbox_xaxis_top = (
            ax.xaxis.get_ticklabel_extents(renderer))
        bbox_yaxis_left, bbox_yaxis_right = (
            ax.yaxis.get_ticklabel_extents(renderer))

        bbox_yaxis_label = ax.yaxis.label.get_window_extent(renderer)
        bbox_xaxis_label = ax.xaxis.label.get_window_extent(renderer)

        # Calculate the width of the left margin.
        yaxis_width = axbbox.x0 - bbox_yaxis_left.x0
        ylabel_width = bbox_yaxis_label.width
        left_margin = (
            yaxis_width + ylabelpad + ylabel_width + figborderpad
            ) / figbbox.width

        # Calculate the width of the right margin.
        xaxis_width = max(
            bbox_xaxis_bottom.x1 - axbbox.x1,
            bbox_xaxis_top.x1 - axbbox.x1,
            0)
        right_margin = (xaxis_width + figborderpad) / figbbox.width

        # Calculate bottom margin height.
        xaxis_height = axbbox.y0 - bbox_xaxis_bottom.y0
        xlabel_height = bbox_xaxis_label.height
        bottom_margin = (
            xaxis_height + xlabel_height + xlabelpad + figborderpad
            ) / figbbox.height

        # Calculate top margin height.
        top_margin = (
            figborderpad
            ) / figbbox.height

        ax.set_position([
            left_margin,
            bottom_margin,
            1 - left_margin - right_margin,
            1 - bottom_margin - top_margin
            ])

        # Setup the yaxis ticks position and limits.
        if len(self._total_values):
            max_total_value = np.max(self._total_values)

            ax.set_yticks(
                [y for y in range(0, max_total_value, 50)])

            anno_total_height = 3 * 10/72 * self.dpi
            ymax = (
                axbbox.height * max_total_value /
                (axbbox.height - anno_total_height - 5/72 * self.dpi))

            ax.axis(ymax=ymax, ymin=-5)

    def setup_axes(self):
        """Setup the main axes and the axes to hold the legend."""
        # Setup the axes to hold the data.
        ax = self.add_axes([0, 0, 1, 1], zorder=1)
        ax.set_facecolor('1')
        ax.grid(
            axis='y', color='0.85', linestyle='-',
            linewidth=self.gridlinewidth)
        ax.set_axisbelow(True)
        for loc in ax.spines:
            ax.spines[loc].set_visible(False)
        ax.tick_params(axis='both', which='both', length=0)

        ax.set_ylabel(
            # _("Number of stations "),
            'Nombre de stations',
            fontsize=self.labelfontsize, labelpad=self.ylabelpad)
        ax.set_xlabel(
            # _("Extent of data acquisition period (years)"),
            "Étendue de la période d'acquisition des données (années)",
            fontsize=self.labelfontsize, labelpad=self.xlabelpad)
        self.canvas.draw()

    def setup_legend(self):
        """
        Setup the legend of the figure.
        """
        active_rec = Rectangle((0, 0), 1, 1, fc=BLUE, ec='none')
        inactive_rec = Rectangle((0, 0), 1, 1, fc=RED, ec='none')

        lines = [active_rec, inactive_rec]
        labels = [_("Actives"), _("Inactives")]

        # Plot the legend.
        leg = self.axes[0].legend(
            lines, labels, numpoints=1, fontsize=10, ncol=1,
            loc='upper right')
        leg.draw_frame(False)
        self.canvas.draw()

    def plot_barchart(self, obswells_data_overview, obswells_data,
                      bins=(0, 1, 2, 3, 4, 5, 10, 15, 20, 25, 30, 40, 50),
                      bwidth=0.75):
        ax = self.axes[0]
        self.bins = bins

        self._data = obswells_data_overview[['last_date', 'first_date']].copy()
        self._data['nyears'] = (
            self._data['last_date'] -
            self._data['first_date']
            ) / np.timedelta64(1, 'Y')
        self._data['is_station_active'] = obswells_data['is_station_active']

        self._total_values = tuple(
            (self._data['nyears'] >= x).sum() for x in bins)
        self._inactive_values = tuple(
            (self._data[~self._data['is_station_active']]['nyears'] >= x).sum()
            for x in bins)
        self._active_values = tuple(
            x2 - x1 for x2, x1 in
            zip(self._total_values, self._inactive_values))

        xpos = list(range(len(bins)))

        # Setup the barplots.

        # We add a vertical offset so that the bottom of the bars align
        # with the bottom of the vertical axis.
        offset = ScaledTranslation(
            0/72, -self.gridlinewidth/2/72, self.dpi_scale_trans)

        if self._active_bar_container is not None:
            self._active_bar_container.remove()
        self._active_bar_container = ax.bar(
            xpos, self._total_values, bwidth, color=BLUE,
            transform=ax.transData + offset)

        if self._inactive_bar_container is not None:
            self._inactive_bar_container.remove()
        self._inactive_bar_container = ax.bar(
            xpos, self._inactive_values, bwidth, color=RED,
            transform=ax.transData + offset)

        # Plot text values over the barplot.
        for anno in self._active_values_annotations:
            anno.remove()
        for anno in self._inactive_values_annotations:
            anno.remove()
        for anno in self._total_values_annotations:
            anno.remove()

        offset = ScaledTranslation(0/72, 1/72, self.dpi_scale_trans)
        self._inactive_values_annotations = tuple(
            ax.text(
                x, y, str(value), ha='center', va='bottom',
                fontsize=10, color=RED, transform=ax.transData + offset)
            for x, y, value in
            zip(xpos, self._total_values, self._inactive_values)
            )

        offset = ScaledTranslation(0/72, 11/72, self.dpi_scale_trans)
        self._active_values_annotations = tuple(
            ax.text(
                x, y, str(value), ha='center', va='bottom',
                fontsize=10, color=BLUE, transform=ax.transData + offset)
            for x, y, value in
            zip(xpos, self._total_values, self._active_values)
            )

        offset = ScaledTranslation(0/72, 21/72, self.dpi_scale_trans)
        self._total_values_annotations = tuple(
            ax.text(
                x, y, str(value), ha='center', va='bottom',
                fontsize=10, color='black', transform=ax.transData + offset)
            for x, y, value in
            zip(xpos, self._total_values, self._total_values)
            )

        # Setup the xaxis.
        ax.set_xticks(xpos)
        ax.set_xticklabels(["\u2265"+str(v) for v in bins])
        ax.axis(xmin=min(xpos) - 0.5, xmax=max(xpos) + 0.5)

        self.canvas.draw()


# %%

if __name__ == '__main__':
    import sys
    from sardes.database.accessors import DatabaseAccessorSardesLite

    dbaccessor = DatabaseAccessorSardesLite(
        'D:/Desktop/rsesq_prod_06-07-2021_tests.db')

    obswells_data = dbaccessor.get_observation_wells_data()
    obswells_data_overview = dbaccessor.get_observation_wells_data_overview()
    
    app = QApplication(sys.argv)

    widget = NetworkBarchartWidget()
    widget.canvas.figure.plot_barchart(obswells_data_overview, obswells_data)
    widget.show()

    sys.exit(app.exec_())
