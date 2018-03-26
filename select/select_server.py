# _*_ coding: utf-8 _*_
"""Servidor que usa la llamada al sistema select."""

import select
import socket
import queue


BUFFER = 1024


def servidor(direccion, proceso):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setblocking(0)
    server.bind(direccion)
    server.listen(5)
    print('Servidor escuchando en {}:{}...'.format(*direccion))

    inputs = [server]
    outputs = []
    message_queues = {}

    while inputs:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)

        # Handle inputs
        for s in readable:

            if s is server:
                # A "readable" socket is ready to accept a connection
                connection, client_address = s.accept()
                print('Cliente conectado desde: {}:{}'.format(*client_address))

                connection.setblocking(0)
                inputs.append(connection)

                # Give the connection a queue for data we want to send
                message_queues[connection] = queue.Queue()

            else:
                data = s.recv(BUFFER)
                if data:
                    # A readable client socket has data
                    message_queues[s].put(data)

                    # Add output channel for response
                    if s not in outputs:
                        outputs.append(s)

                else:
                    # Interpret empty result as closed connection
                    # Stop listening for input on the connection
                    if s in outputs:
                        outputs.remove(s)
                    inputs.remove(s)
                    s.close()

                    # Remove message queue
                    del message_queues[s]
                    # Handle outputs

        # Handle outputs
        for s in writable:
            try:
                next_msg = message_queues[s].get_nowait()
            except queue.Empty:
                # No messages waiting so stop checking for writability.
                outputs.remove(s)
            except KeyError:
                pass
            else:
                # Ejecución de la función pasada por parámetro, que recibe
                # los datos recibidos como entrada y devuelve los datos a
                # enviar como resultado.
                salida = proceso(next_msg)
                s.send(salida)

        # Handle "exceptional conditions"
        for s in exceptional:
            # Stop listening for input on the connection
            inputs.remove(s)
            if s in outputs:
                outputs.remove(s)
            s.close()

            # Remove message queue
            del message_queues[s]
