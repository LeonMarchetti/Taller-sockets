# coding=utf-8
from re import match
import socket
from urllib.parse import urlparse

BUFFER = 1024

# PROXY = '151.80.159.18'
# PROXY = '201.76.9.56'
# PROXY = '103.10.52.83'
# PROXY = '185.71.80.3' # Conexion rechazada

PROXY = ('89.236.17.108', 3128)


def enviar(s, datos):
    while datos:
        enviado = s.send(datos)
        datos = datos[enviado:]


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
                    cl_match = match(r'^Content-Length: (\d+)$', header)
                    if cl_match:
                        content_length = int(cl_match.group(1))
                        break


def GET(url, proxy=False):

    if not match(r'^https?:\/\/', url):
        url = 'http://' + url

    url_obj = urlparse(url)
    
    dominio = url_obj.netloc

    if proxy:
        direccion = PROXY
        request_uri = url
    else:
        direccion = (dominio, 80)

        request_uri = url_obj.path
        if request_uri == '':
            request_uri = '/'

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.connect(direccion)

        # Enviar pedido:
        pedido = armar_pedido(request_uri, dominio)
        enviar(servidor, pedido)

        respuesta = recibir(servidor)

        # Recibir respuesta HTTP:
        return respuesta


def armar_pedido(uri, nombre_host):
    get_linea = 'GET {} HTTP/1.1\r\n'.format(uri)
    print(get_linea.replace('\r\n', ''))
    
    conn_linea = 'Connection: close\r\n'
    
    if nombre_host:
        host_linea = 'Host: {}\r\n'.format(nombre_host)
    else:
        host_linea = ''
        
    pedido = get_linea + host_linea + conn_linea + '\r\n'
    return pedido.encode()


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
            quit()

        usar_proxy = input('Usar proxy? (s/n) > ')
        if usar_proxy in 'sS':
            http_resp = GET(url, True)
        elif usar_proxy in 'nN':
            http_resp = GET(url)
        else:
            quit()
            
        header, html = parsear_http(http_resp)

        guardar(html)
        log_header_http(url, header)
        mostrar_resultado_http(header)

    except ConnectionRefusedError:
        print('Conexión rechazada...')
    except TimeoutError:
        print('Tiempo agotado.')
