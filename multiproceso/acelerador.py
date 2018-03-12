# coding=utf-8
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


def guarderia(signum, frame):
    '''When a child process exits, the kernel sends a SIGCHLD signal. The
    parent process can set up a signal handler to be asynchronously notified of
    that SIGCHLD event and then it can wait for the child to collect its
    termination status, thus preventing the zombie process from being left
    around.'''
    while True:
        try:
            pid, estado = os.waitpid(-1, os.WNOHANG)
        except OSError:
            return

        if pid == 0:
            return


def enviar(s, datos):
    while datos:
        enviado = s.send(datos)
        if enviado == 0:
            raise ConexionTerminadaExcepcion()
        datos = datos[enviado:]


def recibir_completo(s):
    content_length = 0
    datos = b''
    while True:
        # Recibo datos del stream
        cacho = s.recv(BUFFER)
        if not cacho:
            return datos

        datos += cacho

        # Busco el límite de la cabecera
        f = datos.find(b'\r\n\r\n')
        if f > -1:
            if content_length:
                # Si tengo el content-length, sigo recibiendo datos hasta que
                # el total de bytes recibido sea el largo del header + el largo
                # del contenido
                if len(datos) >= f + content_length:
                    return datos
            else:
                # Busco el Content-Length:
                lista_headers = datos[:f].decode().split('\r\n')
                for header in lista_headers:
                    cl_match = re.match(r'^Content-Length: (\d+)$', header)
                    if cl_match:
                        content_length = int(cl_match.group(1))
                        break


def parsear_url(url):
    '''Parsea la url ingresada, obteniendo el host a donde enviar la solicitud
    y el recurso a solicitar.'''
    # Formateo la url ingresada:
    if not re.match(r'^https?:\/\/', url):
        url = 'http://' + url

    oURL = urlparse(url)

    recurso = oURL.path
    if recurso == '':
        recurso = '/'

    return oURL.netloc, recurso


def HEAD(host, recurso):
    '''Realiza una solicitud "HEAD". Regresa el mensaje recibido y el código de
    estado.'''
    
    # Armo pedido HEAD:
    head_linea = 'HEAD {} HTTP/1.1\r\n'.format(recurso)
    print(head_linea.replace('\r\n', ''))
    conn_linea = 'Connection: close\r\n'
    host_linea = 'Host: {}\r\n'.format(host)
    pedido = head_linea + conn_linea + host_linea + '\r\n'

    # Comunicación con el servidor.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.connect((host, 80))

        enviar(servidor, pedido.encode())

        # Recibo la respuesta:
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

        respuesta ''.join([cacho.decode() for cacho in cachos])

        # Obtengo el código de estado:
        linea_estado = respuesta[:respuesta.find(b'\r\n')].decode('ISO-8859-1')
        print(linea_estado)
        codigo = int(re.match(r'^HTTP/\d\.\d (\d{3}) [\w ]+$', linea_estado)[1])

        return respuesta, codigo


def parsear_HEAD(encabezado):
    '''Analiza el encabezado para determinar si archivo se puede descargar
    de a partes, y la longitud del archivo.'''
    
    acepta_rango = False
    longitud = 0
    for linea in encabezado:
        ar_match = re.match(r'^Accept-Ranges: (.*)$)', linea)
        if ar_match:
            if match.group(1) == 'bytes':
                acepta_rango = True
        cl_match = re.match(r'^Content-Length: (\d+)$', header)
        if cl_match:
            longitud = int(cl_match.group(1))
    
    return acepta_rango, longitud


def descargar(url, cantidad_forks):
    host, recurso = parsear_url(url)
    head_resp, head_cod = HEAD(host, recurso)
    if head_cod in range(200, 300):
        acepta_rango, longitud = parsear_HEAD(head_resp.decode('ISO-8859-1'))
        if acepta_rango:
            rangos = []
            longitud_cacho = longitud // cantidad_forks
            for i in range(cantidad_forks):
                rangos.append('bytes={0}-{1}'.format((i*longitud_cacho), 
                                                     ((i+1)*longitud_cacho)))
                                                     
            
        else:
            pass
    else:
        print('No se puede descargar el archivo.')
    
    

    try:
        cliente = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        cliente.bind((host, port))
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
                hijo(cliente)
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


def hijo(cliente):
    try:
        # Recibir pedido:
        pedido = recibir(cliente)

        # Enviar resultado:
        enviar(cliente, resultado)

    except ConexionTerminadaExcepcion:
        print('Conexión terminada')
    finally:
        print('Cerrando hijo...')
        cliente.close()


def main():
    try:
        # Parámetros de la línea de comandos:
        opts, _ = getopt.getopt(sys.argv[1:], 'f:u:')

        # Obtengo el url y la cantidad de forks por parámetro:
        url = '' # url
        forks = 0    # Cantidad de forks
        for opt, arg in opts:
            if opt == '-f':
                forks = int(arg)
            if opt == '-u':
                url = arg

        if url and forks:
            descargar(url, forks)

    except getopt.GetoptError:
        print('Error con los parámetros: ' + str(sys.argv))


if __name__ == '__main__':
    main()
