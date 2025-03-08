from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from datetime import datetime, time, timedelta
import logging
from functools import wraps
from flask import session, redirect, url_for, flash


# Configurar logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Crear la instancia de Flask
app = Flask(__name__)
app.secret_key = 'your_secret_key'

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='1234',
        database='entradasalidapersonal'
    )

def obtener_horario_actual(cursor, punto, dia_actual):
    """Obtiene el horario según el punto y día actual"""
    try:
        cursor.execute('''
            SELECT h.Jornada, h.Horaini, h.Horafin, j.Name 
            FROM horario h
            JOIN jornada j ON h.Jornada = j.Id
            WHERE h.Punto = %s AND h.Dia = %s 
            ORDER BY h.Jornada
        ''', (punto, dia_actual))
        horarios = cursor.fetchall()
        
        # Validar y convertir los horarios
        horarios_procesados = []
        for horario in horarios:
            jornada_id = horario[0]
            hora_ini = horario[1]
            hora_fin = horario[2]
            nombre_jornada = horario[3]
            
            # Asegurarse de que hora_ini y hora_fin sean objetos time
            if isinstance(hora_ini, timedelta):
                hora_ini = (datetime.min + hora_ini).time()
            if isinstance(hora_fin, timedelta):
                hora_fin = (datetime.min + hora_fin).time()
                
            horarios_procesados.append((jornada_id, hora_ini, hora_fin, nombre_jornada))
            
        return horarios_procesados
    except Exception as e:
        logger.error(f"Error en obtener_horario_actual: {str(e)}")
        raise

def obtener_marcaciones_dia(cursor, cedula, fecha_actual):
    """Obtiene las marcaciones del día para un empleado"""
    cursor.execute('''
        SELECT Timestamp 
        FROM activities 
        WHERE Dni = %s 
        AND DATE(Timestamp) = %s 
        ORDER BY Timestamp
    ''', (cedula, fecha_actual))
    return cursor.fetchall()

def validar_tiempo_entre_marcaciones(ultima_marcacion):
    """Valida que hayan pasado al menos 5 minutos desde la última marcación"""
    if ultima_marcacion:
        try:
            ultima_marca = ultima_marcacion[0]
            if isinstance(ultima_marca, tuple):
                ultima_marca = ultima_marca[0]
            
            tiempo_transcurrido = datetime.now() - ultima_marca
            minutos_transcurridos = tiempo_transcurrido.total_seconds() / 60
            return minutos_transcurridos >= 5
        except Exception as e:
            logger.error(f"Error en validar_tiempo_entre_marcaciones: {str(e)}")
            raise
    return True

def esta_en_rango_horario(hora_actual: time, hora_inicio: time, hora_fin: time) -> bool:
    """
    Compara si una hora está dentro de un rango de tiempo.
    """
    try:
        def time_to_minutes(t: time) -> int:
            return t.hour * 60 + t.minute

        actual_mins = time_to_minutes(hora_actual)
        inicio_mins = time_to_minutes(hora_inicio)
        fin_mins = time_to_minutes(hora_fin)
        
        return inicio_mins <= actual_mins <= fin_mins
    except Exception as e:
        logger.error(f"Error en esta_en_rango_horario - hora_actual: {type(hora_actual)}, " +
                    f"hora_inicio: {type(hora_inicio)}, hora_fin: {type(hora_fin)}")
        raise

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        cedula = request.form['Cedula']

        if not cedula.isdigit():
            flash('La cédula debe ser un número.', 'error')
            return redirect(url_for('home'))

        cedula = int(cedula)
        now = datetime.now()
        fecha_actual = now.date()
        hora_actual = now.time()

        dia_actual = str(now.weekday() + 1)
        if dia_actual == '7':
            dia_actual = '0'

        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute('''
                SELECT p.Name, p.Dependencia, d.Punto, d.Name as DependenciaName
                FROM persons p
                JOIN dependencia d ON p.Dependencia = d.Id
                WHERE p.Dni = %s AND p.State = 1
            ''', (cedula,))
            
            empleado = cursor.fetchone()
            if not empleado:
                flash('Empleado no encontrado o inactivo.', 'error')
                return redirect(url_for('home'))

            nombre, dependencia_id, punto, dependencia_nombre = empleado
            
            # Log para debugging
            logger.debug(f"Punto del empleado: {punto}")

            horarios = obtener_horario_actual(cursor, punto, dia_actual)
            if not horarios:
                flash(f'No hay horarios definidos para este día en {dependencia_nombre}.', 'error')
                return redirect(url_for('home'))

            marcaciones = obtener_marcaciones_dia(cursor, cedula, fecha_actual)
            
            if marcaciones and not validar_tiempo_entre_marcaciones(marcaciones[-1]):
                flash('Debe esperar al menos 5 minutos entre marcaciones.', 'error')
                return redirect(url_for('home'))

            registro_realizado = False

            for jornada_id, hora_inicio, hora_fin, nombre_jornada in horarios:
                # Log para debugging
                logger.debug(f"Verificando horario - Jornada: {jornada_id}, " +
                           f"Inicio: {type(hora_inicio)}, Fin: {type(hora_fin)}")
                
                if esta_en_rango_horario(hora_actual, hora_inicio, hora_fin):
                    num_marcaciones = len(marcaciones)
                    
                    minutos_diff = ((hora_actual.hour * 60 + hora_actual.minute) - 
                                  (hora_inicio.hour * 60 + hora_inicio.minute))

                    if jornada_id == 3:  # Jornada continua
                        if num_marcaciones == 0:
                            mensaje = f"Bienvenido {nombre} - Entrada Jornada Continua"
                            tipo_mensaje = 'success' if minutos_diff <= 15 else 'warning'
                        else:
                            mensaje = f"Hasta luego {nombre} - Salida Jornada Continua"
                            tipo_mensaje = 'success'
                    else:  # Jornada normal
                        if num_marcaciones % 2 == 0:
                            if minutos_diff <= 0:
                                mensaje = f"Bienvenido {nombre} - Entrada {nombre_jornada}"
                                tipo_mensaje = 'success'
                            elif minutos_diff <= 15:
                                mensaje = f"{nombre} - Entrada {nombre_jornada} (Llegada tarde: {minutos_diff} minutos)"
                                tipo_mensaje = 'warning'
                            else:
                                mensaje = f"{nombre} - Entrada {nombre_jornada} (Llegada tarde: {minutos_diff} minutos)"
                                tipo_mensaje = 'error'
                        else:
                            mensaje = f"Hasta luego {nombre} - Salida {nombre_jornada}"
                            tipo_mensaje = 'success'

                    cursor.execute('''
                        INSERT INTO activities (Dni, Timestamp) 
                        VALUES (%s, %s)
                    ''', (cedula, now))
                    conn.commit()
                    
                    flash(mensaje, tipo_mensaje)
                    registro_realizado = True
                    break

            if not registro_realizado:
                flash(f'Fuera del horario de registro para {dependencia_nombre}.', 'error')

        except Exception as e:
            logger.error(f"Error en el sistema: {str(e)}", exc_info=True)
            flash(f'Error en el sistema: {str(e)}', 'error')
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('home'))

    return render_template('formularioinput.html')



def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:  # Verificar si el usuario ha iniciado sesión
            flash('Debes iniciar sesión para acceder a esta página.', 'error')
            return redirect(url_for('login'))  # Redirigir al login
        return f(*args, **kwargs)
    return wrapper


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute('''
                SELECT * FROM usuarios
                WHERE username = %s AND password = %s AND estado = 'activo'
            ''', (username, password))
            usuario = cursor.fetchone()

            if usuario:
                # Almacenar el ID del usuario en la sesión
                session['user_id'] = usuario['id']
                session['rol'] = usuario['rol']  # Almacenar el rol del usuario en la sesión
                flash('Inicio de sesión exitoso.', 'success')
                return redirect(url_for('Comfachannel'))  # Redirigir a la bandeja de entrada
            else:
                flash('Usuario o contraseña incorrectos, o el usuario está inactivo.', 'error')
        except Exception as e:
            logger.error(f"Error en el sistema: {str(e)}")
            flash('Error en el sistema.', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('Login.html')


@app.route('/inbox')
@login_required  
def Comfachannel():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Usar dictionary=True para obtener resultados como diccionarios
    try:
        cursor.execute('''
            SELECT * FROM requerimientos
            ORDER BY fecha_envio DESC
        ''')
        requerimientos = cursor.fetchall()
    except Exception as e:
        logger.error(f"Error al obtener requerimientos: {str(e)}")
        flash('Error al cargar los requerimientos.', 'error')
        requerimientos = []
    finally:
        cursor.close()
        conn.close()

    return render_template('Gestioncorreo.html', requerimientos=requerimientos)


@app.route('/requerimientos', methods=['GET', 'POST'])
def requerimientos():
    if request.method == 'POST':
        asunto = request.form.get('asunto')
        perfil = request.form.get('perfil')
        mensaje = request.form.get('mensaje')

        # Depuración: Verifica si los datos llegan correctamente
        print(f"Asunto: {asunto}, Perfil: {perfil}, Mensaje: {mensaje}")

        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Depuración: Verifica la consulta SQL
            print("Ejecutando consulta SQL...")
            cursor.execute('''
                INSERT INTO requerimientos (asunto, perfil, mensaje)
                VALUES (%s, %s, %s)
            ''', (asunto, perfil, mensaje))
            conn.commit()
            print("Datos insertados correctamente.")  # Depuración
            flash('Requerimiento enviado correctamente.', 'success')
        except Exception as e:
            logger.error(f"Error al enviar requerimiento: {str(e)}")
            flash('Error al enviar el requerimiento.', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('requerimientos'))

    return render_template('Gestioncorreo.html')


if __name__ == '__main__':
    app.run(debug=True, port=4000)  