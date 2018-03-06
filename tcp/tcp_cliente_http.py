# coding=utf-8
import os
import os.path
import re
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
                    cl_match = re.match(r'^Content-Length: (\d+)$', header)
                    if cl_match:
                        content_length = int(cl_match[1])
                        break


def parsear_url(url):
    # Formateo la url ingresada:
    if not re.match(r'^https?:\/\/', url):
        url = 'http://' + url

    oURL = urlparse(url)

    absolute_host = oURL.scheme + '://' + oURL.netloc

    host = oURL.netloc

    pagina = oURL.path
    if pagina == '':
        pagina = '/'

    return absolute_host, host, pagina


def GET(absolute_host, host, recurso, proxy=False):
    # Elijo la dirección y puerto a la que me voy a conectar según si uso un
    # proxy o no:
    if proxy:
        direccion = PROXY
        request_uri = absolute_host + recurso
    else:
        direccion = (host, 80)
        request_uri = recurso

    # Armo el pedido:
    get_linea = 'GET {} HTTP/1.1\r\n'.format(request_uri)
    print(get_linea.replace('\r\n', ''))
    conn_linea = 'Connection: close\r\n'
    host_linea = 'Host: {}\r\n'.format(host)

    pedido = get_linea + host_linea + conn_linea + '\r\n'

    # Abro la conexión con el servidor y envío el pedido:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.connect(direccion)

        enviar(servidor, pedido.encode())

        # Recibo la respuesta:
        respuesta = recibir(servidor)

        # Obtengo el código de estado:
        linea_estado = respuesta[:respuesta.find(b'\r\n')].decode('ISO-8859-1')
        print(linea_estado)
        codigo = int(re.match(r'^HTTP/\d\.\d (\d{3}) [\w ]+$', linea_estado)[1])

        return respuesta, codigo


def parsear_http(mensaje):
    # Separar encabezado de html:
    s = mensaje.find(b'\r\n\r\n')
    if s == -1:
        raise Exception('Error: No se encontro separador de HTTP')

    # return header, body
    return mensaje[:s], mensaje[s + 4:]


def loggear_header(header, titulo):
    # Guardo header en un archivo de log:
    str_header = header.decode('ISO-8859-1').replace('\r\n', '\n') + '\r\n'
    log = '[{0}]\n{1}'.format(titulo, str_header)
    with open('paginas/log.txt', 'a') as archivo:
        archivo.write(log)


def guardar(carpeta, nombre_archivo, datos):
    os.makedirs(os.path.dirname(carpeta + '/' + nombre_archivo), exist_ok=True)
    with open(carpeta + '/' + nombre_archivo, 'wb') as archivo:
        archivo.write(datos)


def crear_carpeta(nombre_carpeta):
    # Si ya se había guardado la página antes, se crea una carpeta con un
    # nombre seguido de un número:
    i = 2
    nombre_base = nombre_carpeta
    while os.path.isdir(nombre_carpeta):
        nombre_carpeta = nombre_base + str(i)
        i += 1

    os.makedirs(nombre_carpeta)


def buscar_redireccion(header):
    match_location = re.search(r'Location: (.*)\r\n', header)
    if match_location:
        return match_location[1]
    else:
        raise Exception('Destino de redirección no encontrado...')


def main():
    print('Ingrese pagina a buscar:')
    url = input('> ')
    if url == '':
        quit()

    # Indico si quiero usar el proxy:
    usar_proxy = input('Usar proxy? (s/n) > ')
    if usar_proxy in 'sS':
        proxy = True
    elif usar_proxy in 'nN':
        proxy = False
    else:
        quit()

    while True:
        absolute_host, host, pagina = parsear_url(url)

        # Armo y envío el pedido al servidor, y obtengo la respuesta:
        try:
            http_resp, estado = GET(absolute_host, host, pagina, proxy)
            if estado in (302):
                # Si obtengo un mensaje de redirección, obtengo el nuevo
                # destino y busco de vuelta
                http_header, _ = parsear_http(http_resp)
                url = buscar_redireccion(http_header.decode('ISO-8859-1'))
                continue
            else:
                break
        except ConnectionRefusedError:
            print('Conexión rechazada...')
            quit()
        except TimeoutError:
            print('Tiempo agotado para esta solicitud...')
            quit()

    # Separo header del cuerpo:
    http_header, http_body = parsear_http(http_resp)

    loggear_header(http_header, url)

    html = http_body.decode('ISO-8859-1')

    # Busco el título de la pagina:
    title_search = re.search(r'<title>\s*(.*)\s*</title>', html)
    if title_search:
        titulo = title_search[1]
    else:
        print('Titulo no encontrado')
        titulo = host + pagina
    titulo = titulo.strip().replace(' ', '_')

    # Creo la carpeta donde guardar la página:
    carpeta = 'paginas/' + titulo

    crear_carpeta(carpeta)

    guardar(carpeta, titulo + '.html', http_body)

    # Busco las referencias externas en el html:
    pattern = re.compile(r'(?:href|src)=\"([\w/-]*\.(\w*))\"')
    for (nombre_archivo, ext) in re.findall(pattern, html):
        if ext not in ('html'):
            # Hago un GET de todos los recursos, salvo los html y php:
            try:
                resp, _ = GET(absolute_host, host, '/' + nombre_archivo, proxy)
            except ConnectionRefusedError:
                print('Conexión rechazada...')
                break
            except TimeoutError:
                print('Tiempo agotado para esta solicitud...')
                continue

            header, body = parsear_http(resp)
            guardar(carpeta, nombre_archivo, body)


if __name__ == '__main__':
    main()
