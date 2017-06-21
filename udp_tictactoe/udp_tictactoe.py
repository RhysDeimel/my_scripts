import argparse
import socket
import json

MAX_BYTES = 655355

board = ['', '', '',
         '', '', '',
         '', '', '']


NUMBERS = [1, 2, 3, 4, 5, 6, 7, 8, 9]


def board_print(fill):
    print("""\
        {:^3}|{:^3}|{:^3}
         ---------
        {:^3}|{:^3}|{:^3}
         ---------
        {:^3}|{:^3}|{:^3}""".format(*fill))


def check_win():
    players = ['X', 'O']
    global board

    line1 = [x for x in board[0:3]]
    line2 = [x for x in board[3:6]]
    line3 = [x for x in board[6:9]]
    col1 = [x for x in board[0:8:3]]
    col2 = [x for x in board[1:9:3]]
    col3 = [x for x in board[2:10:3]]
    diag1 = [x for x in board[0:10:4]]
    diag2 = [x for x in board[2:8:2]]

    for sym in players:
        if (line1.count(sym) == 3 or
            line2.count(sym) == 3 or
            line3.count(sym) == 3 or
            col1.count(sym) == 3 or
            col2.count(sym) == 3 or
            col3.count(sym) == 3 or
            diag1.count(sym) == 3 or
            diag2.count(sym) == 3):
                print("\nPlayer {} wins!\n".format(players.index(sym) + 1))
                return True
    if '' not in board:
        print("It's a tie.")
        return True


def do_turn(player):
    """
    Takes user input and checks for validity. If valid, exits
    """
    global board
    print("\nYou are player '{}'. Please enter a valid grid number:\n".format(player))
    while True:
        try:
            selection = int(input('>>> '))
            if selection in NUMBERS and not board[selection - 1]:
                board[selection - 1] = player
                break
            elif selection not in NUMBERS:
                print("I'm sorry, I don't understand. Please try again.")
            else:
                print("I'm sorry, that move has already been made. Please try again")
                continue
        except (IndexError, ValueError):
            print("I'm sorry, I don't understand. Please try again.")
            continue


def player1_client(hostname, port):
    global board
    sock = socket.socket(type=socket.SOCK_DGRAM)
    # get ip to connect to
    sock.connect((hostname, port))
    print('\n============================\n| Welcome to UDP TicTacToe |\n============================\n')
    print('Currently the board is empty. We will use the following grid system:\n')
    board_print(NUMBERS)

    while True:
        do_turn('X')
        if check_win():
            data = json.dumps(board)
            sock.send(data.encode('utf-8'))
            board_print(board)
            break
        print("\nThank you. Please wait for the other player to finish their turn\n")
        data = json.dumps(board)
        sock.send(data.encode('utf-8'))
        response = sock.recv(MAX_BYTES)
        response = response.decode('utf-8')
        response = json.loads(response)
        board = response[:]
        print("\nPlayer 2 made their move. The board is as follows:\n")
        board_print(board)
        if check_win():
            break


def player2_server(interface, port):
    global board
    sock = socket.socket(type=socket.SOCK_DGRAM)
    sock.bind((interface, port))
    print('\n============================\n| Welcome to UDP TicTacToe |\n============================\n')
    print('Currently the board is empty. We will use the following grid system:\n')
    board_print(NUMBERS)
    print("\nWaiting for the other player. Please be patient.")
    while True:
        data, address = sock.recvfrom(MAX_BYTES)
        data = data.decode('utf-8')
        data = json.loads(data)
        board = data[:]
        print("\nPlayer 1 made their move. The board is as follows:\n")
        board_print(board)
        if check_win():
            break
        do_turn('O')
        if check_win():
            response = json.dumps(board)
            sock.sendto(response.encode('utf-8'), address)
            board_print(board)
            print('')
            break
        print("\nThank you. Please wait for the other player to finish their turn\n")
        response = json.dumps(board)
        sock.sendto(response.encode('utf-8'), address)


if __name__ == '__main__':
    choices = {'client': player1_client, 'server': player2_server}
    parser = argparse.ArgumentParser(description='Send and receive UDP,'
                                     ' pretending packets are often dropped')
    parser.add_argument('role', choices=choices, help='which role to play')
    # call with "" to act as a wildcard and accept from 0.0.0.0
    parser.add_argument('host', help='interface the server listens at;'
                        'host the client sends to')
    parser.add_argument('-p', metavar='PORT', type=int, default=1060,
                        help='UDP port (default 1060)')
    args = parser.parse_args()
    function = choices[args.role]  # closure - binds either server or client to function
    function(args.host, args.p)  # invokes bound function with port
