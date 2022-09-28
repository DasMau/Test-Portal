from flask import Flask, render_template, request, redirect, url_for, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditor, CKEditorField
from flask_bootstrap import Bootstrap
import json
import requests
from datetime import date
import pandas as pd
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
import io
import os
from office365.sharepoint.client_context import ClientContext
from office365.sharepoint.files.file import File
from dotenv import load_dotenv

load_dotenv()



app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get("SECRET_DB")
ckeditor = CKEditor(app)
Bootstrap(app)


##CREATE DATABASE



# app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:///colgados.db"

# migracion a PosgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URL", "sqlite:///colgados.db")

#Optional: But it will silence the deprecation warning in the console.
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))



##CREATE TABLE
class Colgado(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    part_key = db.Column(db.Integer, unique=False, nullable=False)
    part_no = db.Column(db.String(250), unique=False, nullable=False)
    pieza_rack = db.Column(db.Integer, unique=False, nullable=False)
    rack_eslabon = db.Column(db.Integer, unique=False, nullable=False)

    # Optional: this will allow each book object to be identified by its title when printed.
    def __repr__(self):
        return f'<Colgados {self.title}>'


db.create_all()

all_colgados = []

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100))
    name = db.Column(db.String(250), unique=False, nullable=False)

db.create_all()

# WTForm
class AddForm(FlaskForm):
    part_key = IntegerField("Part Key", validators=[DataRequired()])
    part_no = StringField("Numero de Parte (Part_No)", validators=[DataRequired()])
    pieza_rack = IntegerField("Piezas por Rack", validators=[DataRequired()])
    rack_eslabon = IntegerField("Racks por Eslabon", validators=[DataRequired()])
    submit = SubmitField("Agregar")

@app.route('/')
# @login_required
def home():

    if current_user.is_authenticated == False:
        return redirect (url_for('login'))


    return render_template("index.html", logged_in=current_user.is_authenticated)

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":

        if User.query.filter_by(email=request.form.get('email')).first():
            #User already exists
            flash("Este correo ya esta registrado, para ingresar inicie sesion")
            return redirect(url_for('login'))

        hash_and_salted_password = generate_password_hash(
            request.form.get('password'),
            method='pbkdf2:sha256',
            salt_length=8
        )
        new_user = User(
            email=request.form.get('email'),
            name=request.form.get('name'),
            password=hash_and_salted_password,
        )
        db.session.add(new_user)
        db.session.commit()
        login_user(new_user)
        return redirect(url_for("secrets"))

    return render_template("register.html", logged_in=current_user.is_authenticated)

@app.route('/login', methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        user = User.query.filter_by(email=email).first()
        # Email doesn't exist or password incorrect.
        if not user:
            flash("El correo proporcionado no esta registrado, intente de nuevo o registrese.")
            return redirect(url_for('login'))
        elif not check_password_hash(user.password, password):
            flash('La contraseña ingresada no es correcta, intente de nuevo por favor.')
            return redirect(url_for('login'))
        else:
            login_user(user)
            return redirect(url_for('secrets'))

    return render_template("login.html", logged_in=current_user.is_authenticated)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/secrets')
@login_required
def secrets():
    print(current_user.name)
    return render_template("secrets.html", name=current_user.name, logged_in=True)



@app.route("/lista_de_colgados")
@login_required
def lista_de_colgados():
    all_colgados = db.session.query(Colgado).all()
    return render_template("lista_de_colgados.html", colgados=all_colgados)

@app.route("/atributos_Lineas")
@login_required
def atributos_lineas():
    return render_template("atributos_lineas.html")


@app.route("/add", methods=["GET", "POST"])
@login_required
def add():
    form = AddForm()
    if form.validate_on_submit():
        new_colgado = Colgado(
            part_key = form.part_key.data,
            part_no = form.part_no.data,
            pieza_rack = form.pieza_rack.data,
            rack_eslabon = form.rack_eslabon.data
        )
    # if request.method == "POST":
    #     new_colgado = Colgado(
    #         part_key = request.form["part_key"],
    #         part_no = request.form["part_no"],
    #         pieza_rack = request.form["pieza_rack"],
    #         rack_eslabon = request.form["rack_eslabon"]
    #     )
        db.session.add(new_colgado)
        db.session.commit()
        return redirect(url_for('lista_de_colgados'))
    return render_template("add.html", form=form)

@app.route("/edit", methods=["GET","POST"])
@login_required
def edit():
    if request.method == "POST":
        # Actualizar Registro
        colgado_id = request.form["id"],
        colgado_actualizar = Colgado.query.get(colgado_id)
        colgado_actualizar.pieza_rack = request.form["pieza_rack"]
        colgado_actualizar.rack_eslabon = request.form["rack_eslabon"]
        db.session.commit()
        return redirect(url_for('lista_de_colgados'))
    colgado_id = request.args.get('id')
    colgado_seleccionado = Colgado.query.get(colgado_id)
    return render_template("edit.html", colgado=colgado_seleccionado)

@app.route("/delete")
@login_required
def delete():
    colgado_id = request.args.get('id')

    #Borra registro
    colgado_borrar = Colgado.query.get(colgado_id)
    db.session.delete(colgado_borrar)
    db.session.commit()
    return redirect(url_for('lista_de_colgados'))



#--------------------funcionalidad para traer rates de produccion de PLEX------------
@app.route("/rates_actuales")
@login_required
def get_rate():
    ds_endpoint = "https://scanpaintmx1.on.plex.com/api/datasources/4494/execute"

    headers = {
        "Authorization": os.getenv("AUT_PLEX"),
        "Content-Type": "application/json;charset=utf-8",
        "Accept": "application/json",
        "Accept-Encoding": "application/gzip",
    }

    json_request = {
        "inputs": {
            "Part_Key": 6220439,
            "Part_Operation_Key": 31460695
        }
    }

    response = requests.post(url=ds_endpoint, json=json_request, headers=headers)

    data_dict = json.loads(response.text)
    data_dict2 = data_dict["tables"][0]
    data_list_rows = data_dict2["rows"]
    data_list_columns = data_dict2["columns"]

    return render_template("rates_actuales.html", rows=data_list_rows, columns= data_list_columns)


    # data = response.json()
    # df = pd.io.json.json_normalize(data)
    # temp = df.to_dict("records")
    # columnNames = df.columns.values
    # return render_template("test_json_plex.html", records=temp, colnames=columnNames)

    # data1 = response.json()
    # data = pd.io.json.json_normalize(data1)
    # temp_dict = data.to_dict(orient='records')
    # return render_template('rates_actuales.html', rates = temp_dict)

    # data1 = response.json()

    # return data1

#--------------------Test para json PLEX a HTML Table------------
@app.route("/test_json_plex")
@login_required
def test():
    with open("plex_api2.json") as data:
        data_lines2 = data.read()
        data_json2 = json.loads(data_lines2)
        data_dict2 = data_json2["tables"][0]
        data_dict_rows = data_dict2["rows"]
        data_dict_columns = data_dict2["columns"]

    return render_template("test_json_plex.html", rows=data_dict_rows, columns=data_dict_columns)


#--------------------Test para json PLEX con sharepoint a HTML Table------------
@app.route("/test_json_plex_sharepoint")
@login_required
def test_json_plex_sharepoint():
    url = "https://scanpaint.sharepoint.com/sites/Innovacion"

    username = os.getenv("SHAREPOINT_USER")
    password = os.getenv("SHAREPOINT_PASS")

    ctx = ClientContext(url).with_user_credentials(username, password)
    # file_url = '/sites/team/Shared Documents/big_buck_bunny.mp4'
    relative_url = "/sites/Innovacion/Shared Documents/Test PLEX/Worcenter_Rates_json.json"

    response = File.open_binary(ctx, relative_url)

    # save data to BytesIO stream
    bytes_file_obj = io.BytesIO()
    bytes_file_obj.write(response.content)
    bytes_file_obj.seek(0)  # set file object to start

    # read file into pandas dataframe
    df = pd.read_json(bytes_file_obj)
    data_json = df.to_json()
    data_dic = json.loads(data_json)

    html_data = df.to_html()

    return render_template("test_json_plex_sharepoint.html", data=html_data, pdf=df)

if __name__ == "__main__":
    app.run(debug=True)