# -*- coding: utf-8 -*-
"""Functionality for adding, editing and viewing adversaries."""

##### IMPORTS #####

import logging

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from ttrpgm.auth import login_required
from ttrpgm.db import get_db

##### CONSTANTS #####

LOG = logging.getLogger(__name__)


##### CLASSES & FUNCTIONS #####

bp = Blueprint("adversary", __name__, url_prefix="/adversary")


@bp.route("/")
@login_required
def index():
    db = get_db()
    adversaries = db.execute(
        "SELECT a.id, name, health, stress, author_id, username, created"
        " FROM adversary a JOIN user u ON a.author_id = u.id"
        " WHERE u.id = ?"
        " ORDER BY created DESC",
        (g.user["id"],),
    ).fetchall()
    return render_template("adversary/index.html", adversaries=adversaries)


@bp.route("/add", methods=("GET", "POST"))
@login_required
def add():
    if request.method == "POST":
        title = request.form["name"]
        health = request.form["health"]
        stress = request.form["stress"]

        error = None

        if not title:
            error = "Name is required."
        elif not health:
            error = "Health is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                "INSERT INTO adversary (name, health, stress, author_id)" " VALUES (?, ?, ?, ?)",
                (title, health, stress, g.user["id"]),
            )
            db.commit()
            return redirect(url_for("adversary.index"))

    return render_template("adversary/add.html")

def get_adversary(id, check_author=True):
    adversary = get_db().execute(
        'SELECT a.id, name, health, stress, created, author_id, username'
        ' FROM adversary a JOIN user u ON a.author_id = u.id'
        ' WHERE a.id = ?',
        (id,)
    ).fetchone()

    if adversary is None:
        abort(404, f"Adversary id {id} doesn't exist.")

    if check_author and adversary['author_id'] != g.user['id']:
        abort(403)

    return adversary

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    adversary = get_adversary(id)

    if request.method == 'POST':
        title = request.form["name"]
        health = request.form["health"]
        stress = request.form["stress"]

        error = None

        if not title:
            error = "Name is required."
        elif not health:
            error = "Health is required."

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE adversary SET name = ?, health = ?, stress = ?'
                ' WHERE id = ?',
                (title, health, stress, id)
            )
            db.commit()
            return redirect(url_for('adversary.index'))

    return render_template('adversary/update.html', post=adversary)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_adversary(id)
    db = get_db()
    db.execute('DELETE FROM adversary WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('adversary.index'))

