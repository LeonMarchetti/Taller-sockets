# _*_ coding: utf-8 _*_
"""
Parámetros:
* -s: Modo servidor
* -c: Modo cliente
* -i: Dirección IP (Opcional)
* -p: Número de puerto (Opcional)
* -q: Archivo sql (Opcional)
"""
import getopt
import json
import select_server
import socket
import sqlite3
import sys


BUFFER = 1024


# Comunicación ===============================================================
class ConexionTerminadaExcepcion(Exception):
    pass


def enviar(s, datos):
    while datos:
        enviado = s.send(datos)
        datos = datos[enviado:]


def recibir(s):
    cachos = b''
    while True:
        cacho = s.recv(BUFFER)
        if cacho:
            cachos += cacho
            if len(cachos) > 4:

                longitud = int.from_bytes(cachos[:4], byteorder='big')
                if len(cachos) >= longitud + 4:
                    return cachos[4:4 + longitud]
        else:
            raise ConexionTerminadaExcepcion


# Servidor ===================================================================
sqlite_cursor = None


def iniciar_servidor(direccion):
    global sqlite_cursor

    sqlite_conexion = sqlite3.connect('acs-1-year-2015.sqlite')
    sqlite_cursor = sqlite_conexion.cursor()

    select_server.servidor(direccion, procesar_query)


def procesar_query(datos):
    sql = datos.decode().strip()
    print('Query: {}'.format(sql))
    if sqlite3.complete_statement(sql):
        try:
            sqlite_cursor.execute(sql)
            resultado = sqlite_cursor.fetchall()
            if resultado:
                mensaje = json.dumps(resultado).encode()

            else:
                mensaje = 'Esta consulta no regresó resultados.'.encode()

        except sqlite3.Error as e:
            mensaje = e.args[0].encode()
            print('Error: {}'.format(mensaje))

        else:
            print('OK')

    else:
        mensaje = 'La/s sentencias sql no están completas.'.encode()
        print('Error: {}'.format(mensaje))

    return len(mensaje).to_bytes(4, byteorder='big') + mensaje


# Cliente ====================================================================
def mostrar_resultado(filas):
    salida = []
    print('Filas: {}'.format(len(filas)))
    for fila in filas:
        salida.append('\t'.join([str(e) for e in fila]))

    print('\n'.join(salida))


def cliente(direccion, query):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect(direccion)
        s.send(query.encode())

        datos = recibir(s)
        if datos:
            try:
                filas = json.loads(datos.decode())
            except json.JSONDecodeError:
                print(datos.decode())
            else:
                print('Resultado:')
                mostrar_resultado(filas)
        else:
            print('No hay nada que mostrar')


def sacar_query(archivo):
    with open(archivo, encoding='utf-8-sig') as archivo:
        return archivo.read()


# ============================================================================
if __name__ == '__main__':
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'csi:p:h:q:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
        host = 'localhost'
        port = 10000
        modo = ''
        query_string = ''

        for opt, arg in opts:
            if opt == '-c':  # Modo Cliente
                if modo == '':
                    modo = 'c'
                else:
                    print('Error... no se puede ser cliente y servidor al '
                          'mismo tiempo!')
                    sys.exit(1)
            elif opt == '-s':  # Modo Servidor
                if modo == '':
                    modo = 's'
                else:
                    print('Error... no se puede ser cliente y servidor al '
                          'mismo tiempo!')
                    sys.exit(1)
            elif opt == '-i':  # Dirección IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)
            elif opt == '-q':
                query_string = sacar_query(arg)

        if modo == '':
            print('Usar "-c" para modo Cliente y "-s" para modo Servidor')
        elif modo == 's':
            iniciar_servidor((host, port))
        elif modo == 'c':
            if not query_string:
                query_string = input('Ingresar query > ')
            cliente((host, port), query_string)
