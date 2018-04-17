﻿# -*- coding: utf-8 -*-
"""
Parámetros:
* -d <dir> Directorio donde guardar la página y sus recursos asociados.
* -u <url> URL de la página a solicitar
"""
import getopt
import os
import os.path
import re
import signal
import socket
import sys
from urllib.parse import urlparse


class ConexionTerminadaExcepcion(Exception):
    pass


# noinspection PyUnusedLocal
def guarderia(signum, frame):
    """When a child process exits, the kernel sends a SIGCHLD signal. The
    parent process can set up a signal handler to be asynchronously notified of
    that SIGCHLD event and then it can wait for the child to collect its
    termination status, thus preventing the zombie process from being left
    around.
    """
    while True:
        try:
            pid, estado = os.waitpid(-1, os.WNOHANG)
        except OSError:
            return

        if pid == 0:
            return


def parsear_url(_url):
    if not re.match(r'^https?:\/\/', _url):
        _url = 'http://' + _url

    obj_url = urlparse(_url)

    pagina = obj_url.path
    if pagina == '':
        pagina = '/'

    return obj_url.netloc, pagina


def loggear_header(titulo, linea_estado, headers):
    log = '[{0}]\r\n{1}\r\n'.format(titulo, linea_estado)
    for k in headers:
        log += '{}: {}\r\n'.format(k, headers[k])
    log += '\r\n'

    with open('log.txt', 'a') as archivo:
        archivo.write(log)


def parsear_header(header):
    header_lineas = header.split(b'\r\n')

    # Separo la línea estado y obtengo el código de estado:
    linea_estado = header_lineas.pop(0).decode('ISO-8859-1')
    print(linea_estado)

    # Armo el diccionario con los encabezados:
    headers_dict = {}
    for linea in header_lineas:
        linea_str = linea.decode('ISO-8859-1')
        n = linea_str.find(': ')
        headers_dict[linea_str[:n]] = linea_str[n + 2:]

    return linea_estado, headers_dict


def recibir_http(s):
    # Primero recibo el header:
    cachos = b''
    f = -1
    while f == -1:
        cacho = s.recv(1024)
        if cacho:
            cachos += cacho
            f = cachos.find(b'\r\n\r\n')

        else:
            raise ConexionTerminadaExcepcion

    # Proceso el header:
    linea_estado, headers = parsear_header(cachos[:f])
    cachos = cachos[f + 4:]

    # Ahora recibo el cuerpo:
    if 'Content-Length' in headers:
        content_length = int(headers['Content-Length'])
        while len(cachos) < content_length:
            cacho = s.recv(1024)
            if cacho:
                cachos += cacho
            else:
                raise ConexionTerminadaExcepcion

    else:
        # Si el mensaje no trae la longitud del contenido entonces recibo
        # bytes hasta que se termine la conexión:
        while True:
            cacho = s.recv(1024)
            if cacho:
                cachos += cacho
            else:
                break

    # Regreso el código de estado, los encabezados y el cuerpo:
    return linea_estado, headers, cachos


def get(host, recurso):
    # Armo el pedido:
    lineas = (
        'GET {} HTTP/1.1\r\n'.format(recurso),
        'Connection: close\r\n',
        'Host: {}\r\n'.format(host),
    )
    print(lineas[0].replace('\r\n', ''))
    pedido = '{}\r\n'.format(''.join(lineas))

    # Abro la conexión con el servidor y envío el pedido:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as socket_servidor:
        socket_servidor.connect((host, 80))
        socket_servidor.sendall(pedido.encode())
        return recibir_http(socket_servidor)


def get_codigo(linea_estado):
    codigo_match = re.match(r'^HTTP/\d\.\d (\d{3}) [\w ]+$', linea_estado)
    if codigo_match:
        return int(codigo_match.group(1))
    else:
        raise RuntimeError('No hubo match de código...')


def guardar(_carpeta, nombre_archivo, datos):
    os.makedirs(os.path.dirname(_carpeta + '/' + nombre_archivo),
                exist_ok=True)
    with open(_carpeta + '/' + nombre_archivo, 'wb') as archivo:
        archivo.write(datos)


def crear_carpeta(nombre_carpeta):
    """Crea la carpera pasada por parámetro. Si la carpeta ya existe, se crea
    una carpeta cuyo nombre es igual al parámetro seguido de un número
    secuencial.
    """
    i = 2
    nombre_base = nombre_carpeta
    while os.path.isdir(nombre_carpeta):
        nombre_carpeta = nombre_base + str(i)
        i += 1

    os.makedirs(nombre_carpeta)
    return nombre_carpeta


def get_codificacion(headers):
    encoding = 'ISO-8859-1'
    if 'Content-Type' in headers:
        content_type_match = re.search(r'charset=(.*)', headers['Content-Type'])
        if content_type_match:
            encoding = content_type_match.group(1)

    return encoding


# noinspection PyProtectedMember
def buscar(_carpeta, _url):
    while True:
        host, pagina = parsear_url(_url)
        # Armo y envío el pedido al servidor, y obtengo la respuesta:
        try:
            linea_estado, headers, cuerpo = get(host, pagina)
            loggear_header('{}{}'.format(host, pagina), linea_estado, headers)

        except ConexionTerminadaExcepcion:
            print('Conexión rechazada...')
            quit()

        except TimeoutError:
            print('Tiempo agotado para esta solicitud...')
            quit()

        else:
            if get_codigo(linea_estado) in (301, 302,):
                # Si obtengo un mensaje de redirección, obtengo el nuevo
                # destino y busco de vuelta
                if 'Location' in headers:
                    _url = headers['Location']
                    continue
                else:
                    raise RuntimeError('Destino de redirección no '
                                       'encontrado...')

            else:
                break

    # Decodifico el cuerpo:
    contenido = cuerpo.decode(get_codificacion(headers))

    # Busco el título de la página:
    titulo_search = re.search(r'<title>\s*(.*)\s*</title>', contenido)
    if titulo_search:
        titulo = titulo_search.group(1)
    else:
        print('Titulo no encontrado')
        titulo = host + pagina
    titulo = titulo.strip().replace(' ', '_').replace(':', '_')

    # Creo la carpeta donde guardar la página:
    _carpeta += titulo
    _carpeta = crear_carpeta(_carpeta)
    guardar(_carpeta, '{}.html'.format(titulo), cuerpo)

    signal.signal(signal.SIGCHLD, guarderia)

    # Busco las referencias externas en el html:
    pattern = re.compile(r'(?:href|src)=\"([\w/-]*\.(\w*))\"')
    for (nombre_archivo, ext) in re.findall(pattern, contenido):
        if ext not in ('html',):
            # Hago un GET de todos los recursos, salvo los html:
            pid = os.fork()
            if pid == 0:
                # Proceso hijo:
                try:
                    linea_estado, headers, cuerpo = get(host,
                                                        '/' + nombre_archivo)
                    loggear_header('{}/{}'.format(host, nombre_archivo),
                                   linea_estado,
                                   headers)
                    if cuerpo:
                        guardar(_carpeta, nombre_archivo, cuerpo)

                except ConexionTerminadaExcepcion:
                    print('[{}] Conexión rechazada...'.format(os.getpid()))

                except TimeoutError:
                    print('[{}] Tiempo agotado para esta solicitud...'.format(
                        os.getpid()))

                finally:
                    os._exit(0)

            else:
                # Proceso padre:
                print('Forkeado a proceso: {}'.format(pid))


if __name__ == '__main__':
    # Parámetros de la línea de comandos:
    try:
        opts, _ = getopt.getopt(sys.argv[1:], 'd:u:')
    except getopt.GetoptError as error:
        print('Error con el parámetro {0.opt}: {0.msg}'.format(error))
    else:
        carpeta = 'paginas/'
        proxy = False
        url = ''

        for opt, arg in opts:
            if opt == '-d':  # Carpeta
                carpeta = arg
                if carpeta[-1] not in '/\\':
                    carpeta += '/'

            elif opt == '-u':  # URL
                url = arg

        if url:
            buscar(carpeta, url)
        else:
            print('Falta indicar la URL.')
