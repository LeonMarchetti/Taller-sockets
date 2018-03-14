# coding=utf-8
'''
Parámetros:
* -d Directorio donde guardar la página y sus recursos asociados.
* -u URL de la página a solicitar
'''

import getopt
import os
import os.path
import re
import urllib.parse
import signal
import socket
import sys


BUFFER = 1024


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


def parsear_url(url):
    '''Formatea un string url, para obtener el host y el recurso a acceder.
    '''
    if not re.match(r'^https?:\/\/', url):
        url = 'http://' + url

    oURL = urllib.parse.urlparse(url)

    pagina = oURL.path
    if pagina == '':
        pagina = '/'

    return oURL.netloc, pagina


def enviar(s, datos):
    '''Envía datos a través de un socket.
    '''
    while datos:
        enviado = s.send(datos)
        datos = datos[enviado:]


def recibir_HTTP(s):
    '''Recibe un mensaje HTTP a través de un socket.
    '''
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


def GET(host, recurso):
    '''Realiza el pedido GET de un recurso. Regresa  el mensaje recibido y el
    código de estado.
    '''
    # Armo el pedido:
    get_linea = 'GET {} HTTP/1.1\r\n'.format(recurso)
    print(get_linea.strip())
    conn_linea = 'Connection: close\r\n'
    host_linea = 'Host: {}\r\n'.format(host)

    pedido = get_linea + host_linea + conn_linea + '\r\n'

    # Abro la conexión con el servidor y envío el pedido:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as servidor:
        servidor.connect((host, 80))

        enviar(servidor, pedido.encode())

        # Recibo la respuesta:
        respuesta = recibir_HTTP(servidor)

        # Obtengo el código de estado:
        linea_estado = respuesta[:respuesta.find(b'\r\n')].decode('ISO-8859-1')
        print(linea_estado)
        codigo = int(re.match(r'^HTTP/\d\.\d (\d{3}) [\w ]+$',
                              linea_estado).group(1))

        return respuesta, codigo


def parsear_http(mensaje):
    '''Separa el encabezado y el cuerpo de un mensaje HTTP.
    '''
    s = mensaje.find(b'\r\n\r\n')
    if s == -1:
        raise Exception('Error: No se encontro separador de HTTP')

    return mensaje[:s], mensaje[s + 4:]


def buscar_redireccion(header):
    '''Encuentra el próximo destino de una comunicación HTTP analizando el
    encabezado de un mensaje HTTP con código 302.
    '''
    match_location = re.search(r'Location: (.*)\r\n', header)
    if match_location:
        return match_location.group(1)
    else:
        raise Exception('Destino de redirección no encontrado...')


def loggear_header(encabezado, titulo):
    '''Guarda el encabezado en un archivo de log.
    '''
    str_header = encabezado.decode('ISO-8859-1').replace('\r\n', '\n') + '\r\n'
    log = '[{0}]\n{1}'.format(titulo, str_header)
    with open('log.txt', 'a') as archivo:
        archivo.write(log)


def crear_carpeta(nombre_carpeta):
    '''Crea la carpera pasada por parámetro. Si la carpeta ya existe, se crea
    una carpeta cuyo nombre es igual al parámetro seguido de un número
    secuencial.
    '''
    i = 2
    nombre_base = nombre_carpeta
    while os.path.isdir(nombre_carpeta):
        nombre_carpeta = nombre_base + str(i)
        i += 1

    os.makedirs(nombre_carpeta)

    return nombre_carpeta


def guardar(carpeta, nombre_archivo, datos):
    '''Guarda los datos en el archivo.
    '''
    # Extraigo la barra de directorio del nombre del archivo, si lo tuviera:
    try:
        match = re.match(r'\/?(.*)', nombre_archivo)
        path_archivo = os.path.join(carpeta, match.group(1))

        os.makedirs(os.path.dirname(path_archivo), exist_ok=True)

        with open(path_archivo, 'wb') as archivo:
            archivo.write(datos)
    except Exception as e:
        print('{}'.format(e))
        raise


def buscar_titulo(html):
    '''Busca el título de una página HTML.
    '''
    title_search = re.search(r'<title>\s*(.*)\s*</title>', html)
    if title_search:
        return title_search.group(1).strip()
    else:
        return ''


def recuperar(url, dir):
    '''Recupera la página web indica por la url y la almacena en el directorio
       indicado.
    '''
    # Primero pido la página principal
    # Realizo el pedido hasta que no me siga redirigiendo:
    while True:
        host, pagina = parsear_url(url)

        # Armo y envío el pedido al servidor, y obtengo la respuesta:
        try:
            http_resp, estado = GET(host, pagina)
            if estado in (302,):
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

    # Creo la carpeta donde guardar la página:
    dir = crear_carpeta(dir)

    # Guardo el archivo:
    if pagina in ('', '/'):
        # Busco el título de la página:
        titulo = buscar_titulo(html)
        if titulo:
            archivo = titulo.replace(' ', '_') + '.html'
        else:
            archivo = url.replace('.', '_dot_') + '.html'
    else:
        archivo = pagina

    guardar(dir, archivo, http_body)

    signal.signal(signal.SIGCHLD, guarderia)

    # Busco las referencias externas en el html:
    pattern = re.compile(r'(?:href|src)=\"([\w/-]*\.(\w*))\"')
    for (nombre_archivo, ext) in re.findall(pattern, html):
        if ext not in ('html',):
            # Hago un GET de todos los recursos, salvo los html:
            pid = os.fork()
            if pid == 0:
                # Proceso hijo:
                try:
                    resp, _ = GET(host, '/' + nombre_archivo)
                    header, body = parsear_http(resp)
                    if body:
                        guardar(dir, nombre_archivo, body)

                except ConnectionRefusedError:
                    print('Conexión rechazada...')
                except TimeoutError:
                    print('Tiempo agotado para esta solicitud...')
                finally:
                    os._exit(0)

            else:
                # Proceso padre:
                print('Forkeado a proceso: {}'.format(pid))


def main(argv):
    '''Función principal.
    '''
    try:
        # Parámetros de la línea de comandos:
        opts, _ = getopt.getopt(argv[1:], 'd:u:')

        dir = ''
        url = ''

        for opt, arg in opts:
            if opt == '-d':  # Directorio/Carpeta
                dir = arg
            elif opt == '-u':  # URL
                url = arg

        if url:
            if dir:
                recuperar(url, dir)
            else:
                recuperar(url, 'paginas')

    except getopt.GetoptError:
        print('Error con los parámetros: ' + str(argv))


if __name__ == '__main__':
    main(sys.argv)
