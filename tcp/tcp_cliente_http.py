import socket
from urllib.parse import urlparse

class MiExcepcion(Exception):
    pass

BUFFER = 1024
# PROXY = '151.80.159.18'
PROXY = '201.76.9.56'

DEBUG = True

def GET(url, proxy=None):

    if proxy:
        HOST = proxy
        get_path = url
    else:
        url_obj = urlparse(url)

        get_path = url_obj.path
        if get_path == '':
            get_path = '/'

        HOST = url_obj.netloc

    PORT = 80

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        # Enviar pedido:
        servidor.connect((HOST, PORT))
        servidor.send('GET {} HTTP/1.1\r\n\r\n'.format(get_path).encode())

        # Recibir respuesta HTTP:
        cachos = []
        while True:
            cacho = servidor.recv(BUFFER)
            if (cacho == b'') or (cacho.find(b'</html>') > -1):
                cachos.append(cacho)
                break
            cachos.append(cacho)

        return b''.join([cacho for cacho in cachos])

def parsear_http(mensaje):

    # Separar encabezado de html:
    s = http_resp.find(b'\r\n\r\n')
    if s == -1:
        raise Exception('E> No se encontro separador de HTTP')

    return http_resp[:s], http_resp[s+4:]

def log_header_http(url, header):
    str_header = header.decode().replace('\r\n', '\n') + '\r\n'
    log = '[{0}]\n{1}'.format(url, str_header)
    with open('/home/netbookmarchetti/Documentos/Python/tcp/log.txt', 'a') as f:
        f.write(log)

def guardar(mensaje):
    # Guardar contenido html en archivo:
    with open('/home/netbookmarchetti/Documentos/Python/tcp/paginas/tmp.html', 'wb') as f:
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
            http_resp = GET(url, PROXY)
        elif usar_proxy in 'nN':
            http_resp = GET(url)
        else:
            raise MiExcepcion('Salir')

        header, html = parsear_http(http_resp)
        guardar(html)
        log_header_http(url, header)
        mostrar_resultado_http(header)

    except ConnectionRefusedError:
        print('Conexión rechazada...')
    except MiExcepcion as e:
        print('{}'.format(e))
