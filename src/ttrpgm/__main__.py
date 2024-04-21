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
TEMPLATE_FILES = {"monster": pathlib.Path("templates/monster.yml")}

##### CLASSES & FUNCTIONS #####


def main():
    app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])

    tabs = []
    for _, path in TEMPLATE_FILES.items():
        template = data.Template.load_yaml(path)

        dashboard = data.DataDashboard(pathlib.Path(), template)
        tabs.append(dashboard.create())

    app.layout = dash.html.Div(tabs)
    app.run()


if __name__ == "__main__":
    main()
