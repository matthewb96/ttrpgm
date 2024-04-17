# -*- coding: utf-8 -*-
"""Table-top RPG Manager."""

##### IMPORTS #####

import logging
import pathlib

import dash
import dash_bootstrap_components as dbc

from ttrpgm import data

##### CONSTANTS #####

LOG = logging.getLogger(__name__)


##### CLASSES & FUNCTIONS #####


def main():
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    template = data.Template(
        name="monster",
        schema={
            "name": data.InputType.TEXT,
            "health": data.InputType.INTEGER,
            "stress": data.InputType.INTEGER,
            "location": data.InputType.TEXT,
            "features": data.InputType.LONG_TEXT,
        },
        hidden_columns=["features"],
    )

    datatable = data.DataTable(pathlib.Path(), template)

    table = datatable.create()

    app.layout = dash.html.Div([dash.html.Div(children="Hello World"), table])
    app.run()


if __name__ == "__main__":
    main()
