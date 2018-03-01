# coding=utf-8

import re
import socket
from urllib.parse import urlparse

class MiExcepcion(Exception):
    pass

BUFFER = 1024
# PROXY = '151.80.159.18'
PROXY = '201.76.9.56'

DEBUG = True

def enviar(s, mensaje):
    while mensaje:
        n = s.send(mensaje)
        mensaje = mensaje[n:]

    # def recibir(s):
    # cachos = []
    # while True:
    # cacho = s.recv(BUFFER)
    # if (cacho == b''):
    # raise Exception('Conexión terminada')
    # if (cacho.find(b'</html>') > -1) or (cacho.find(b'</HTML>') > -1):
    # cachos.append(cacho)
    # break

    # cachos.append(cacho)

    # return b''.join([cacho for cacho in cachos])

def recibir(s):
    mensaje = b''
    while True:
        recv = s.recv(BUFFER)
        mensaje += recv
        if len(recv) < BUFFER:
            break

    return mensaje

# def recibir(s):
# cacho = s.recv(BUFFER)
# longitud = 0

# f = cacho.find(b'\r\n\r\n')
# if f > -1:
# lista_headers = cacho[:f].decode().split('\r\n')
# for header in lista_headers:
# match = re.match(r'^Content-Length: (\d+)$', header)
# if match:
# longitud = int(match.group(0))

# cuerpo = body[f+4:]
# while longitud > len(cuerpo):
# cuerpo += s.recv(BUFFER)

# return lista_headers + b'\r\n\r\n' cuerpo

def GET(url, proxy=None):
    if proxy:
        HOST = proxy
        get_path = url
    else:
        if url.find('//') == -1:
            url = '//' + url

        url_obj = urlparse(url)

        get_path = url_obj.path
        if get_path == '':
            get_path = '/'

        HOST = url_obj.netloc

    PORT = 80

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.connect((HOST, PORT))

        # Enviar pedido:
        enviar(servidor, 'GET {} HTTP/1.1\r\n\r\n'.format(get_path).encode())

        # Recibir respuesta HTTP:
        return recibir(servidor)

def parsear_http(mensaje):
    # Separar encabezado de html:
    s = http_resp.find(b'\r\n\r\n')
    if s == -1:
        raise Exception('E> No se encontro separador de HTTP')

    return http_resp[:s], http_resp[s + 4:]

def log_header_http(url, header):
    str_header = header.decode().replace('\r\n', '\n') + '\r\n'
    log = '[{0}]\n{1}'.format(url, str_header)
    with open('log.txt', 'a') as f:
        f.write(log)

def guardar(mensaje):
    # Guardar contenido html en archivo:
    with open('paginas/tmp.html', 'wb') as f:
        f.write(mensaje)

def mostrar_resultado_http(header):
    resultado = header[:header.find(b'\r\n')]
    print(resultado.decode())

if __name__ == '__main__':
    try:
        print('Ingrese pagina a buscar:')
        url = input('> ')
        if url == '':
            raise MiExcepcion('Salir')

        url = 'http://{}/'.format(url)

        usar_proxy = input('Usar proxy? (s/n) > ')

        if usar_proxy in 'sS':
            proxy = PROXY
        elif usar_proxy in 'nN':
            proxy = None
        else:
            raise MiExcepcion('Salir')

        http_resp = GET(url, proxy)

        header, html = parsear_http(http_resp)

        guardar(html)
        log_header_http(url, header)
        mostrar_resultado_http(header)

    except ConnectionRefusedError:
        print('Conexión rechazada...')
    except MiExcepcion as e:
        print('{}'.format(e))
    except TimeoutError:
        print('Tiempo agotado.')
