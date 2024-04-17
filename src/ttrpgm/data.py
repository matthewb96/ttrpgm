# -*- coding: utf-8 -*-
"""Functionality for interacting with the various JSON lines datasets."""

##### IMPORTS #####

import dataclasses
import enum
import json
import logging
import pathlib
import re
from typing import Any

import caf.toolkit as ctk
import dash
import dash_bootstrap_components as dbc
import dash_dangerously_set_inner_html
import jinja2
import markdown
import pydantic
from dash import dash_table, dcc, html

##### CONSTANTS #####

LOG = logging.getLogger(__name__)

##### CLASSES & FUNCTIONS #####


class InputType(enum.StrEnum):
    TEXT = enum.auto()
    INTEGER = enum.auto()
    LONG_TEXT = enum.auto()

    @classmethod
    def _missing_(cls, value) -> "InputType":
        value = str(value).strip().lower()

        for i in cls:
            if value == i.value:
                return i

        return None


@dataclasses.dataclass
class DropDownType:
    options: list[str]


class Template(ctk.BaseConfig):

    name: str
    schema: dict[str, InputType | DropDownType]
    hidden_columns: list[str]

    @pydantic.field_validator("name", mode="after")
    @classmethod
    def normalize(cls, value: str) -> str:
        return value.strip().lower()

    @pydantic.field_validator("schema", mode="before")
    @classmethod
    def normalise_schema_names(cls, values: dict) -> dict:
        new_dict: dict[str, InputType | DropDownType] = {}

        for name, type_ in values.items():
            name = name.strip().lower()
            new_dict[name] = type_

        if "name" not in new_dict:
            raise ValueError("all templates must include a name variable")

        return new_dict

    @pydantic.field_validator("hidden_columns", mode="after")
    @classmethod
    def check_hidden_columns(
        cls, values: list[str], info: pydantic.ValidationInfo
    ) -> list:
        new_values = []
        for name in values:
            name = name.strip().lower()
            if name not in info.data["schema"]:
                raise ValueError("hidden column ({name}) not found in schema")
            new_values.append(name)

        return new_values


def _dcc_input(
    type_: InputType | DropDownType,
    name: str,
    id_: str,
    placeholder: str | None = None,
    value: Any | None = None,
    **kwargs,
) -> dbc.Row:
    if placeholder is None:
        placeholder = f"Enter {name.title()}..."

    if isinstance(type_, DropDownType):
        widget = dcc.Dropdown(options=type_.options, value=value, id=id_, **kwargs)
    elif type_ == InputType.TEXT:
        widget = dbc.Input(
            id_, value=value, placeholder=placeholder, type="text", **kwargs
        )
    elif type_ == InputType.INTEGER:
        widget = dbc.Input(
            id_, value=value, placeholder=placeholder, type="number", **kwargs
        )
    elif type_ == InputType.LONG_TEXT:
        widget = dbc.Textarea(id_, value=value, placeholder=placeholder, **kwargs)
    else:
        raise ValueError(f"unknown type {type_}")

    return dbc.Row([dbc.Label(name.title(), width=2), dbc.Col(widget, width=10)])


class DataTable:

    def __init__(self, folder: pathlib.Path, template: Template) -> None:

        self.template = template
        self.name = template.name
        self.data_path = folder / f"{template.name}.json"

        self.data: dict = {}
        if self.data_path.is_file():
            with open(self.data_path, "rt", encoding="utf-8") as file:
                self.data = json.load(file)

        template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(self.data_path.parent / "templates")
        )
        self.display_template = template_env.get_template(f"{self.name}.html")

        self.widget_ids = {
            "submit-button": f"{self.name}-submit-button",
            "input-values": f"{self.name}-input-value",
            "datatable": f"{self.name}-datatable",
            "modal-button": f"{self.name}-modal-button",
            "modal": f"{self.name}-modal",
            "group-table": f"{self.name}-group-table",
        }

        self.update_data("test", {"name": "test", "health": "10"})

    def check_data(self, name: str) -> bool:
        name = name.lower().strip()
        return name in self.data

    def get_data(self, name: str) -> dict:
        return self.data[name.strip().lower()]

    def update_data(self, name: str, values: dict):
        # TODO Add data validation
        name = name.strip().lower()
        self.data[name] = values

        with open(self.data_path, "wt", encoding="utf-8") as file:
            json.dump(self.data, file)

    def create_input_form(self, values: dict[str, Any] | None = None):
        children = []

        add_edit_id = f"{self.name}-add-edit-check"
        name_search_id = f"{self.name}-edit-search-id"

        children.append(
            dbc.RadioItems(
                options=[
                    {"label": f"Add a {self.name.title()}", "value": 1},
                    {"label": f"Edit / View a {self.name.title()}", "value": 2},
                ],
                value=1,
                id=add_edit_id,
                inline=True,
            ),
        )
        children.append(
            _dcc_input(
                DropDownType([i["name"] for i in self.data.values()]),
                "Name Search",
                name_search_id,
                disabled=True,
            )
        )

        input_ids = {}
        for name, type_ in self.template.schema.items():
            id_ = self.widget_ids["input-values"] + f"-{name}"

            if values is not None and name in values:
                value = values[name]
            else:
                value = None

            widget = _dcc_input(type_, name, id_, value=value)
            children.append(widget)
            input_ids[name] = id_

        message_id = f"{self.name}-modal-message-label"
        children.append(dbc.Label(id=message_id))

        @dash.callback(
            dash.Output(name_search_id, "disabled"),
            dash.Output(input_ids["name"], "disabled"),
            dash.Input(add_edit_id, "value"),
        )
        def disable_name(add_edit):
            if add_edit == 1:
                return True, False
            return False, True

        @dash.callback(
            [dash.Output(i, "value") for i in input_ids.values()],
            dash.Input(name_search_id, "value"),
            prevent_initial_call=True,
        )
        def update_values(name):
            data = self.get_data(name)
            # Make sure the data is in the correct order for the outputs
            return tuple(data.get(i) for i in input_ids)

        modal = dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle(f"Add {self.name}")),
                dbc.ModalBody(dbc.Form(children)),
                dbc.ModalFooter(
                    dbc.Button("Submit", self.widget_ids["submit-button"], n_clicks=0)
                ),
            ],
            id=self.widget_ids["modal"],
            is_open=False,
            size="xl",
            scrollable=True,
        )
        button = dbc.Button(
            f"Add, Edit or View a {self.name}", id=self.widget_ids["modal-button"]
        )

        @dash.callback(
            dash.Output(self.widget_ids["modal"], "is_open"),
            dash.Output(self.widget_ids["datatable"], "data"),
            dash.Output(message_id, "children"),
            [
                dash.Input(self.widget_ids["modal-button"], "n_clicks"),
                dash.Input(self.widget_ids["submit-button"], "n_clicks"),
            ],
            dash.State(add_edit_id, "value"),
            dash.State(name_search_id, "value"),
            [dash.State(i, "value") for i in input_ids.values()],
            prevent_initial_call=True,
        )
        def update(n1, n2, add_edit, search_name, *value):
            del n1, n2, value
            trigger = dash.callback_context.triggered_id

            if trigger == self.widget_ids["modal-button"]:
                return True, list(self.data.values()), ""
            if trigger != self.widget_ids["submit-button"]:
                raise ValueError(f"unknown trigger: {trigger}")

            data = {}
            for properties in dash.callback_context.args_grouping:
                match = re.match(
                    rf"{self.widget_ids['input-values']}-(\w+)", properties["id"], re.I
                )
                if match is None:
                    continue

                data[match.group(1)] = properties["value"]

            if add_edit == 2:  # Edit mode use name from dropdown
                data["name"] = search_name
                message = f"Sucessfully updated {data['name']}"

            elif add_edit == 1 and self.check_data(data["name"]):
                # Add mode shouldn't overwrite
                return (
                    True,
                    list(self.data.values()),
                    f"{data['name']} already exists, switch to edit mode",
                )
            elif add_edit == 1:
                message = f"Sucessfully added {data['name']}"

            self.update_data(data["name"], data)

            return False, list(self.data.values()), message

        return modal, button

    def _html_data_display(self, data: dict[str, Any]) -> str:
        data = data.copy()
        for name, value in data.items():
            type_ = self.template.schema.get(name)
            if type_ is None or value is None:
                continue

            if type_ == InputType.LONG_TEXT:
                data[name] = markdown.markdown(value)

        return self.display_template.render(**data)

    def create(self):
        table = dash_table.DataTable(
            [{"id": i, **j} for i, j in self.data.items()],
            columns=[
                {"id": i, "name": i.title()}
                for i in self.template.schema
                if i not in self.template.hidden_columns
            ],
            id=self.widget_ids["datatable"],
            sort_action="native",
            filter_action="native",
            row_selectable=True,
        )
        modal, add_button = self.create_input_form()

        group = dash_table.DataTable(
            [],
            columns=[{"id": i, "name": i.title()} for i in ("name", "count")],
            id=self.widget_ids["group-table"],
            sort_action="native",
            filter_action="native",
            editable=True,
        )

        @dash.callback(
            dash.Output(self.widget_ids["group-table"], "data"),
            dash.Input(self.widget_ids["datatable"], "selected_row_ids"),
            dash.State(self.widget_ids["group-table"], "data"),
            prevent_initial_call=True,
        )
        def update_group(selected_ids, current_data):
            count_lookup = {i["name"]: i["count"] for i in current_data}

            rows = []
            for i in set(selected_ids):
                if i is None:
                    continue

                name = self.get_data(i)["name"]
                rows.append({"name": name, "count": count_lookup.get(name, 1)})
            return rows

        group_name_id = f"{self.name}-group-name"
        group_name = dbc.Input(group_name_id, placeholder="Enter Name of Group...")
        group_display_button_id = f"{self.name}-group-display-button"
        group_display_button = dbc.Button("Display Group", id=group_display_button_id)

        group_modal_display = dbc.Modal(
            id="group-modal-display", is_open=False, fullscreen=True
        )

        @dash.callback(
            dash.Output("group-modal-display", "is_open"),
            dash.Output("group-modal-display", "children"),
            dash.Input(group_name_id, "value"),
            dash.Input(group_display_button, "n_clicks"),
            dash.State(self.widget_ids["group-table"], "data"),
            prevent_initial_call=True,
        )
        def display_group(name, n_clicks, group_data):
            trigger = dash.callback_context.triggered_id
            if trigger == group_name_id or n_clicks == 0:
                return False, []

            children = []
            lengths = []
            for row in group_data:
                data = self.get_data(row["name"])

                html_body = self._html_data_display(data)
                lengths.append(len(html_body))
                children.append(
                    dbc.Card(
                        [
                            dbc.CardHeader(html.H5(data["name"])),
                            dbc.CardBody(
                                dash_dangerously_set_inner_html.DangerouslySetInnerHTML(
                                    html_body
                                )
                            ),
                        ]
                    )
                )

            lengths = iter(lengths)
            children = sorted(children, key=lambda x: next(lengths), reverse=True)
            cols = {0: [], 1: []}
            # TODO Fix grouping into rows
            for i, widget in enumerate(children):
                cols[i % 2].append(dbc.Row(widget))

            return True, [
                dbc.ModalHeader(html.H3(name)),
                dbc.ModalBody(dbc.Row([dbc.Col(i) for i in cols.values()])),
            ]

        div = html.Div(
            [
                dbc.Row(
                    [
                        dbc.Col(html.H2(f"{self.name.title()} Data"), width=10),
                        dbc.Col(html.H2("Group"), width=2),
                    ]
                ),
                dbc.Row(
                    [dbc.Col(table, width=10), dbc.Col([group_name, group], width=2)]
                ),
                dbc.Row(
                    [
                        dbc.Col(add_button, width=10),
                        dbc.Col(group_display_button, width=2),
                    ]
                ),
                modal,
                group_modal_display,
            ]
        )

        return div