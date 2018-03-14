# coding=utf-8
'''
Parámetros:
* -i Dirección IP.
* -p Puerto
'''


import errno
import getopt
import mimetypes
import os
import os.path
import re
import signal
import socket
import subprocess
import sys
import time


class ConexionTerminadaExcepcion(Exception):
    pass


BUFFER = 1024
# BAD_REQUEST = b'HTTP/1.1 400 Solicitud Incorrecta\r\n\r\n'

lineas_status = {
    200: 'HTTP/1.0 200 OK\r\n',
    400: 'HTTP/1.1 400 Solicitud Incorrecta\r\n',
    404: 'HTTP/1.0 404 No encontrado\r\n',
}

def guarderia(signum, frame):
    '''When a child process exits, the kernel sends a SIGCHLD signal. The
    parent process can set up a signal handler to be asynchronously notified of
    that SIGCHLD event and then it can wait for the child to collect its
    termination status, thus preventing the zombie process from being left
    around.
    '''
    while True:
        try:
            pid, estado = os.waitpid(-1, os.WNOHANG)
        except OSError:
            return

        if pid == 0:
            return


def ejecutar_php(script):
    '''Ejecuta un script php, y regresa la salida estándar.
    '''
    p = subprocess.Popen('php ' + script, shell=True, stdout=subprocess.PIPE)
    return p.stdout.read()


def buscar_recurso(recurso):
    '''Busca un recurso en el disco y regresa el mensaje a mandar a través de
       una conexión HTTP.
    '''
    # Busco el archivo:
    archivo = 'paginas/' + recurso

    tipo_mime = mimetypes.guess_type(recurso)[0]
    if tipo_mime is None:
        tipo_mime = 'text/html'

    if os.path.isfile(archivo):
        status = 'HTTP/1.0 200 OK\r\n'
    else:
        status = 'HTTP/1.0 404 No encontrado\r\n'
        archivo = ('paginas/no_encontrado' +
                   mimetypes.guess_extension(tipo_mime))

    print('Enviando "{}"'.format(status.strip()))

    # Cabeceras de HTTP:
    fecha = 'Date: {}\r\n'.format(time.strftime('%a, %d %b %Y %H:%M:%S %Z',
                                                time.localtime()))
    tipo_contenido = 'Content-Type: {};charset=utf-8\r\n'.format(tipo_mime)

    # Abro el archivo del recurso. Si es un archivo .php entonces lo ejecuto:
    if os.path.splitext(archivo)[1] == '.php':
        body = ejecutar_php(archivo)
    else:
        body = b''
        with open(archivo, 'rb') as f:
            for linea in f:
                body += linea

    # Armo la respuesta:
    return (status.encode() +
            fecha.encode() +
            tipo_contenido.encode() +
            b'\r\n' +
            body)


def procesar(mensaje):
    '''
    '''
    # Parseo la primera línea del pedido, para obtener tipo de pedido y recurso
    linea_pedido = mensaje[:mensaje.find('\r\n')]

    print('Recibido: "{}"'.format(linea_pedido))

    pedido = re.match(r'^(GET|POST) \/(.*) HTTP\/(?:1\.0|1\.1|2\.0)$',
                      linea_pedido)

    if pedido:
        if pedido.group(1) == 'GET':
            uri = pedido.group(2)
            qs = uri.find('?')
            if qs == -1:
                return buscar_recurso(uri)
            else:
                return buscar_recurso(uri[:qs])
        elif pedido.group(1) == 'POST':
            linea_vacia = mensaje.find('\r\n\r\n')
            return buscar_recurso(pedido.group(2), mensaje[linea_vacia+4:])
        else:
            return BAD_REQUEST
    else:
        return BAD_REQUEST


def enviar(s, datos):
    '''Envía datos a través de un socket.
    '''
    while datos:
        enviado = s.send(datos)
        if enviado == 0:
            raise ConexionTerminadaExcepcion()
        datos = datos[enviado:]


def recibir(s):
    '''Recibe un encabezado de http a través de un socket.
    '''
    cachos = []
    while True:
        cacho = s.recv(BUFFER)
        if cacho == b'':
            raise ConexionTerminadaExcepcion()

        f = cacho.find(b'\r\n\r\n')
        if f > -1:
            cachos.append(cacho[:f])
            break
        else:
            cachos.append(cacho)

    return ''.join([cacho.decode() for cacho in cachos])


def ejecutar_php(script):
    '''Ejecuta un script de PHP, devolviendo la salida estándar.
    '''
    p = subprocess.Popen('php ' + script, shell=True, stdout=subprocess.PIPE)
    return p.stdout.read()


def buscar_recurso(pedido):
    '''Analiza el pedido y obtiene el recurso a devolver, el código de estado
       y el tipo mime del recurso.
    '''
    if pedido:
        archivo = 'paginas/' + pedido.group(2)
        estado = 200

        tipo_mime = mimetypes.guess_type(archivo)[0]
        if tipo_mime is None:
            tipo_mime = 'text/plain'

        if not os.path.isfile(archivo):
            # Página/recurso especial por si no se encuentra el recurso:
            archivo = 'paginas/no_encontrado' + mimetypes.guess_extension(tipo_mime)
            estado = 404
    else:
        # Página especial por si el mensaje está mal redactado:
        archivo = 'paginas/bad_request.html'
        estado = 400
        tipo_mime = 'text/html'
        
    return archivo, estado, tipo_mime


def procesar(mensaje):
    '''Analiza el mensaje HTTP recibido, y devuelve el mensaje de respuesta con
       el recurso pedido. Si no se encuentra en el servidor se devuelve una
       página o recurso de no encontrado.
    '''
    linea_pedido = mensaje[:mensaje.find('\r\n')]
    print('Recibido: "{}"'.format(linea_pedido))

    # Parseo el pedido:
    pedido = re.match(r'^(GET|POST) \/([^?=&\s]*)(?:\?(.*))? HTTP\/(?:1\.0|1\.1|2\.0)$',
                      linea_pedido)
    archivo, estado, tipo_mime = buscar_recurso(pedido)

    # Cabeceras de HTTP:
    linea_status = lineas_status[estado]
    print('Enviando "{}"'.format(linea_status))

    linea_date = 'Date: {}\r\n'.format(time.strftime('%a, %d %b %Y %H:%M:%S %Z',
                                                     time.localtime()))

    # Abro el archivo del recurso. Si es un script PHP entonces lo ejecuto:
    if os.path.splitext(archivo)[1] == '.php':
        body = ejecutar_php(archivo)
        tipo_mime = 'text/html'
    else:
        body = b''
        with open(archivo, 'rb') as f:
            for linea in f:
                body += linea

    linea_contenttype = 'Content-Type: {};charset=utf-8\r\n'.format(tipo_mime)
    linea_contentlength = 'Content-Length: {}\r\n'.format(len(body))

    # Armo la respuesta:
    return (linea_status.encode('ISO-8859-1') +
            linea_date.encode('ISO-8859-1') +
            linea_contenttype.encode('ISO-8859-1') +
            linea_contentlength.encode('ISO-8859-1') +
            b'\r\n' +
            body)


def server(host, port):
    '''Atiende pedidos de HTTP, forkeando un subproceso por cada pedido.
    '''
    try:
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((host, port))
        servidor.listen(5)
        print('Escuchando en <{}:{}>'.format(host, port))

        signal.signal(signal.SIGCHLD, guarderia)

        while True:
            print('Esperando conexión...')
            try:
                cliente, direccion = servidor.accept()
            except IOError as e:
                codigo, msg = e.args
                if codigo == errno.EINTR:
                    continue
                else:
                    raise

            # Forkeo el proceso: El hijo  se encarga de atender al cliente
            pid = os.fork()
            if pid == 0:
                servidor.close()

                try:
                    # Recibe pedido y responde:
                    pedido = recibir(cliente)
                    respuesta = procesar(pedido)
                    enviar(cliente, respuesta)

                except ConexionTerminadaExcepcion:
                    print('Conexión terminada')

                finally:
                    print('Cerrando hijo...')
                    cliente.close()
                    os._exit(0)

            else:
                print('Conexión establecida: ' +
                      '<{}:{}> con subproceso <{}>'.format(direccion[0],
                                                           direccion[1],
                                                           pid))
                cliente.close()

    except KeyboardInterrupt:
        print('Programa terminado')
    finally:
        servidor.close()


def main():
    '''Función principal.
    '''
    try:
        # Parámetros de la línea de comandos:
        opts, _ = getopt.getopt(sys.argv[1:], 'i:p:')

        # Valores por defecto para host y puerto:
        # host = 'localhost'
        host = '192.168.1.42'
        port = 8000

        for opt, arg in opts:
            if opt == '-i':  # Dirección IP
                host = arg
            elif opt == '-p':  # Puerto
                port = int(arg)

        server(host, port)

    except getopt.GetoptError:
        print('Error con los parámetros: ' + str(sys.argv))


if __name__ == '__main__':
    main()
