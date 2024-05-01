# -*- coding: utf-8 -*-
"""Functionality for interacting with the various JSON lines datasets."""

##### IMPORTS #####

import collections
import dataclasses
import enum
import json
import logging
import pathlib
import re
from typing import Any, Literal
import warnings

import caf.toolkit as ctk
import jinja2
import markdown
import pandas as pd
import pydantic

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
    group_count_columns: list[str]

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

    @pydantic.field_validator("hidden_columns", "group_count_columns", mode="after")
    @classmethod
    def check_hidden_columns(
        cls, values: list[str], info: pydantic.ValidationInfo
    ) -> list:
        new_values = []
        for name in values:
            name = name.strip().lower()
            if name not in info.data["schema"]:
                raise ValueError("column ({name}) not found in schema")
            new_values.append(name)

        return new_values


class Data:

    def __init__(self, folder: pathlib.Path, template: Template) -> None:

        self.template = template
        self.name = template.name
        self.data_path = folder / f"data/{template.name}.json"

        self.load_data()
        template_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(folder / "templates")
        )
        self.display_template = template_env.get_template(f"{self.name}.html")

    def load_data(self) -> None:
        self.dataframe = pd.read_json(self.data_path, orient="index")
        # TODO Validate columns

    def columns_to_display(self) -> dict[str, str]:
        columns = {}
        for col in self.dataframe:
            if col in self.template.hidden_columns:
                continue

            columns[col] = str(col).strip().replace("_", " ").title()

        return columns

    @staticmethod
    def name_to_id(name: str) -> str:
        name = re.sub(r"[\s-_]+", "_", name.strip().lower())
        name = re.sub(r"[!\"#$%&'()*+,-./:;<=>?@[\]\\^_`{|}~]", "", name, re.I)
        return name

    def check_data(
        self, name: str, error: Literal["ignore", "raise", "warn"] = "ignore"
    ) -> bool:
        name = self.name_to_id(name)
        check = name in self.dataframe.index

        if error == "ignore" or check:
            return check

        msg = f"{name!r} isn't in data"
        if error == "warn":
            warnings.warn(msg, RuntimeWarning)
        raise KeyError(msg)

    def get_data(self, name: str) -> dict:
        self.check_data(name, "raise")
        return self.dataframe.loc[self.name_to_id(name)]

    def backup_database(self) -> None:
        if not self.data_path.is_file():
            warnings.warn("nothing to backup", RuntimeWarning)
            return

        new_path = self.data_path.with_name(self.data_path.stem + ".backup")
        if new_path.is_file():
            new_path.unlink()
        self.data_path.rename(new_path)

    def save_data(self, backup: bool = True) -> None:
        if backup:
            self.backup_database()

        self.dataframe.to_json(self.data_path, orient="index")

    def remove_data(self, name: str) -> None:
        if not self.check_data(name):
            warnings.warn(f"{name!r} not in data so nothing is removed", RuntimeWarning)
            return

        self.dataframe = self.dataframe.drop(index=self.name_to_id(name))
        self.save_data()

    def add_data(self, name: str, values: dict, update: bool = False) -> None:
        if not update and self.check_data(name):
            raise KeyError(
                f"data already present for {name!r}, consider updating instead"
            )
        if update and not self.check_data(name):
            raise KeyError(f"data for {name!r} isn't found, consider adding instead")

        self.dataframe.loc[self.name_to_id(name)] = pd.Series(values)
        self.save_data()

    def _html_data_display(self, data: dict[str, Any]) -> str:
        data = data.copy()
        for name, value in data.items():
            type_ = self.template.schema.get(name)
            if type_ is None or value is None:
                continue

            if type_ == InputType.LONG_TEXT:
                data[name] = markdown.markdown(value)
            elif type_ == InputType.INTEGER:
                data[name] = int(value)

        return self.display_template.render(**data)
