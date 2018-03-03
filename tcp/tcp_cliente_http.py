# coding=utf-8
import re
import socket
from urllib.parse import urlparse


class ConexionTerminadaExcepcion(Exception):
    pass


class MiExcepcion(Exception):
    pass


BUFFER = 1024
# PROXY = '151.80.159.18'
PROXY = '201.76.9.56'


def enviar(s, mensaje):
    while mensaje:
        n = s.send(mensaje)
        mensaje = mensaje[n:]


def recibir(s):
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
                    match = re.match(r'^Content-Length: (\d+)$', header)
                    if match:
                        content_length = int(match.group(1))
                        break


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
        pedido = armar_pedido(get_path, url_obj.netloc)
        enviar(servidor, pedido)
        respuesta = recibir(servidor)

        # Recibir respuesta HTTP:
        return respuesta


def armar_pedido(pedido, nombre_host):
    get_linea = 'GET {} HTTP/1.1\r\n'.format(pedido)
    conn_linea = 'Connection: close\r\n'
    host_linea = 'Host: {}\r\n'.format(nombre_host)
    return get_linea.encode() + host_linea.encode() + conn_linea.encode() + b'\r\n'


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
