# -*- coding: utf-8 -*-
"""
    Functionality for the TKinter based GUI.
"""

##### IMPORTS #####

import logging

import pathlib
import tkinter as tk
import numpy as np
import pandas as pd
import tksheet
from tkinter import ttk

from ttrpgm import data


##### CONSTANTS #####

LOG = logging.getLogger(__name__)


##### CLASSES & FUNCTIONS #####


class demo(tk.Tk):
    def __init__(self):
        tk.Tk.__init__(self)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.frame = tk.Frame(self)
        self.frame.grid_columnconfigure(0, weight=1)
        self.frame.grid_rowconfigure(0, weight=1)
        self.data = [
            ["3", "c", "z"],
            ["1", "a", "x"],
            ["1", "b", "y"],
            ["2", "b", "y"],
            ["2", "c", "z"],
        ]
        self.sheet = Sheet(
            self.frame,
            data=self.data,
            column_width=180,
            theme="dark",
            height=700,
            width=1100,
        )
        self.sheet.enable_bindings(
            "copy",
            "rc_select",
            "arrowkeys",
            "double_click_column_resize",
            "column_width_resize",
            "column_select",
            "row_select",
            "drag_select",
            "single_select",
            "select_all",
        )
        self.frame.grid(row=0, column=0, sticky="nswe")
        self.sheet.grid(row=0, column=0, sticky="nswe")

        self.sheet.dropdown(
            self.sheet.span(n2a(0), header=True, table=False),
            values=["all", "1", "2", "3"],
            set_value="all",
            selection_function=self.header_dropdown_selected,
            text="Header A Name",
        )
        self.sheet.dropdown(
            self.sheet.span(n2a(1), header=True, table=False),
            values=["all", "a", "b", "c"],
            set_value="all",
            selection_function=self.header_dropdown_selected,
            text="Header B Name",
        )
        self.sheet.dropdown(
            self.sheet.span(n2a(2), header=True, table=False),
            values=["all", "x", "y", "z"],
            set_value="all",
            selection_function=self.header_dropdown_selected,
            text="Header C Name",
        )

    def header_dropdown_selected(self, event=None):
        hdrs = self.sheet.headers()
        # this function is run before header cell data is set by dropdown selection
        # so we have to get the new value from the event
        hdrs[event.loc] = event.value
        if all(dd == "all" for dd in hdrs):
            self.sheet.display_rows("all")
        else:
            rows = [
                rn
                for rn, row in enumerate(self.data)
                if all(row[c] == e or e == "all" for c, e in enumerate(hdrs))
            ]
            self.sheet.display_rows(rows=rows, all_displayed=False)
        self.sheet.redraw()


class DataSheet(ttk.Frame):

    def __init__(self, data: data.Data, frame: ttk.Frame) -> None:
        self.data = data

        columns = data.columns_to_display()

        self.sheet = tksheet.Sheet(
            frame,
            headers=list(columns.values()),
            data=data.dataframe.loc[:, list(columns.keys())].values.tolist(),
        )

        self.sheet.enable_bindings(
            "copy",
            "rc_select",
            "arrowkeys",
            "double_click_column_resize",
            "column_width_resize",
            "column_select",
            "row_select",
            "drag_select",
            "single_select",
            "select_all",
        )

        for i, (col, title) in enumerate(columns.items()):
            self.sheet.dropdown(
                self.sheet.span(tksheet.num2alpha(i), header=True, table=False),
                values=["all"] + self.data.dataframe[col].unique().tolist(),
                set_value="all",
                selection_function=self.header_dropdown_selected,
                text=title,
            )

    def header_dropdown_selected(self, event=None):
        hdrs = self.sheet.headers()
        # this function is run before header cell data is set by dropdown selection
        # so we have to get the new value from the event
        hdrs[event.loc] = event.value
        if all(dd == "all" for dd in hdrs):
            self.sheet.display_rows("all")
        else:
            mask = pd.Series(False, index=self.data.dataframe.index)
            for i, val in enumerate(hdrs):
                if val == "all":
                    continue
                print(f"Filtering {i} with {val!r}")
                mask = mask | (self.data.dataframe.iloc[:, i] == val)

            rows = list(np.arange(len(self.data.dataframe))[mask.values])
            self.sheet.display_rows(rows=rows, all_displayed=False)
        self.sheet.redraw()


def _test():
    root = tk.Tk(__package__)

    template = data.Template.load_yaml(pathlib.Path(r"templates\monster.yml"))
    monsters = data.Data(pathlib.Path(), template)

    frame = tk.Frame(root, bg="blue")
    frame.pack(expand=True, fill="both")
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_rowconfigure(0, weight=1)
    sheet = DataSheet(monsters, frame)
    sheet.sheet.grid(column=0, row=0, sticky="NSEW")

    root.mainloop()


if __name__ == "__main__":
    _test()
