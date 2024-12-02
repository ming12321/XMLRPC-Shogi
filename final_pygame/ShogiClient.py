import pygame 
import xmlrpc.client
import time
import threading
# 伺服器位址
SERVER_URL = "http://127.0.0.1:12321/"
server = xmlrpc.client.ServerProxy(SERVER_URL)

# Pygame 初始化
pygame.init()
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("線上將棋")
background_image = pygame.image.load("image/background.jpg")
chessboard_image = pygame.image.load("image/Shogi_board.png")


player1_hand_map = [
    ["L_1", "N_1", "S_1", "G_1"],
    ["B_1", "R_1", "P_1"]
]

player2_hand_map = [
    ["B_2", "R_2", "P_2"],
    ["L_2", "N_2", "S_2", "G_2"]
]


for row, line in enumerate(player1_hand_map):
    for col, chess_name in enumerate(line):
        if chess_name:
            player1_hand_map[row][col] = [pygame.image.load("image/" + chess_name + ".png"), (700 + col * 60, 60 + row * 100)]        
        else:
            player1_hand_map[row][col] = None

for row, line in enumerate(player2_hand_map):
    for col, chess_name in enumerate(line):
        if chess_name:
            player2_hand_map[row][col] = [pygame.image.load("image/" + chess_name + ".png"), (700 + col * 60, 520 + row * 100)]        
        else:
            player2_hand_map[row][col] = None    


WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GRAY = 	(128, 128, 128)
GREEN = (0, 255, 0)
# 字型
gaametitlefont = pygame.font.Font(None, 80)
titlefont = pygame.font.Font(None, 64)
font = pygame.font.Font(None, 40)

# 輸入框
username_input = ""
password_input = ""
active_input = ""

# 訊息顯示
message = ""
logged_in = False  # 追蹤是否已登入
onlinePeopleAccounts = 0
is_selected_chess = False
selected_chess = None
is_choosed_placechess = False
choosed_placechess = None


lock = threading.Lock()

def draw_text(text, x, y, color=BLACK):
    text_surface = font.render(text, True, color)
    screen.blit(text_surface, (x, y))

def draw_titletext(text, x, y, color=BLACK):
    titletext_surface = titlefont.render(text, True, color)
    screen.blit(titletext_surface, (x, y))

def draw_gametitletext(text, x, y, color=BLACK):
    gametitletext_surface = titlefont.render(text, True, color)
    screen.blit(gametitletext_surface, (x, y))

def send_request(action, username, password):
    try:
        if action == 'register':
            response = server.register(username, password)
        elif action == 'login':
            response = server.login(username, password)
        elif action == 'logout':
            response = server.logout(username)
        else:
            return {'status': 'error', 'message': 'Invalid action'}
        
        # 檢查回傳資料是字典格式
        if isinstance(response, dict) and 'status' in response and 'message' in response:
            return response
        else:
            return {'status': 'error', 'message': 'Unexpected server response format'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    
def receive_onlinePeopleAccounts():
    while True:
        with lock: 
            onlinePeopleAccounts = server.onlinePeopleAccounts()
            time.sleep(0.5)
            return onlinePeopleAccounts
        
def receive_neededPeopleAccounts():
    while True:
        with lock: 
            neededPeopleAccounts = server.neededPeopleAccounts()
            time.sleep(0.5)
            return neededPeopleAccounts
        
class GameClient:
    def __init__(self, client_name):
        self.client_name = client_name
        self.server = xmlrpc.client.ServerProxy("http://127.0.0.1:12321/")
        self.lock = threading.Lock()
        self.opponent = None
        self.role = None
        self.game_id = None
        self.matchmaking_thread = None
        self.running = True
        self.matching = False
        self.game_start = False
        self.chessboard_thread = None
        self.player_turn_thread = None
        self.hand = {}
        self.hand_thread = None
        self.opponenthand = {}
        self.opponenthand_thread = None
        self.who_win_thread = None

    def join_queue(self):
        print(f"{self.client_name} 正在等待配對...")
        while self.opponent is None and self.matching:
            try:
                result = self.server.join_queue(self.client_name)
                if result:
                    self.opponent = result["oppoenet"]
                    self.role = result["role"]
                    self.game_id = result["game_id"]
                else:
                    time.sleep(1)
            except Exception as e:
                print(f"無法連接伺服器: {e}")
                break

        if self.opponent and self.role and self.game_id:
            print(f"配對成功！玩家: {self.client_name} 為 {self.role},{self.opponent} 為 {3 - int(self.role)}, game_id = {self.game_id}")
            self.start_game()

    def start_game(self):
        with self.lock:
            if not self.game_start:
                self.game_start = True
                self.chessboard_thread = threading.Thread(target=self.update_chessboard, daemon=True)
                self.chessboard_thread.start()
                self.player_turn_thread = threading.Thread(target=self.update_playerTurn, daemon=True)
                self.player_turn_thread.start()
                self.hand_thread = threading.Thread(target=self.update_playerhand, daemon=True)
                self.hand_thread.start()
                self.opponenthand_thread = threading.Thread(target=self.update_opponenthand, daemon=True)
                self.opponenthand_thread.start()
                self.who_win_thread = threading.Thread(target=self.update_who_win, daemon=True)
                self.who_win_thread.start()
                server.newgame(self.game_id)
    
    def end_game(self):
        with self.lock:
            if self.game_start:
                self.game_start = False
                if self.chessboard_thread:
                    self.chessboard_thread.join()
                if self.player_turn_thread:
                    self.player_turn_thread.join()
                if self.hand_thread:
                    self.hand_thread.join()
                if self.opponenthand_thread:
                    self.opponenthand_thread.join()
                if self.who_win_thread:
                    self.who_win_thread.join()
            

    def update_playerTurn(self):
        with lock:
            playerTurn = None
            playerTurn = self.server.update_turn(self.game_id)
            time.sleep(0.1)
            return playerTurn 
    
    def update_chessboard(self):
        with lock:
            chessboard_map = [[None] * 9 for _ in range(9)]
            chessboard_map = self.server.update_board(self.game_id)  
            for row, line in enumerate(chessboard_map):
                for col, chess_name in enumerate(line):
                    if chess_name:
                        chessboard_map[row][col] = [pygame.image.load("image/" + chess_name + ".png"), (105 + col * 60, 105 + row * 60)]        
                    else:
                        chessboard_map[row][col] = None 



            time.sleep(0.1)
            return chessboard_map 
    
    def update_playerhand(self):
        with lock:
            playerhand  = {}
            playerhand = self.server.update_playerhand(self.role, self.game_id)
            time.sleep(0.1)
            return playerhand 
    
    def update_opponenthand(self):
        with lock:
            opponenthand  = {}
            opponenthand = self.server.update_oppoenethand(self.role, self.game_id)
            time.sleep(0.1)
            return opponenthand 
    
    def update_who_win(self):
        with lock:
            who_win = self.server.is_win(client.game_id) 
            if who_win:
                if(client.role == str(who_win)):
                    return "win"
                else:
                    return "lose"
            time.sleep(0.1)
            return False
    
    def start_matchmaking(self):
        with lock:
            if not self.matching:
                self.matching = True
                self.matchmaking_thread = threading.Thread(target=self.join_queue, daemon=True)
                self.matchmaking_thread.start()

    def cancel_matchmaking(self):
        with lock:
            if self.matching:
                print(f"{self.client_name} 取消配對...")
                self.matching = False
                try:
                    self.server.leave_queue(self.client_name)  # 從伺服器取消佇列
                except Exception as e:
                    self.matching = True
                    print(f"無法取消配對: {e}")
                if self.matchmaking_thread:
                    self.matchmaking_thread.join()

    def stop(self):
        self.running = False
        self.opponent = None
        self.role = None
        self.game_id = None
        self.opponenthand = {}
        self.hand = {}
        self.cancel_matchmaking()
        self.end_game()

def display_chessboard():
    for line_chess in chessboard_map:
        for chess in line_chess:
            if chess:
                screen.blit(chess[0], chess[1])

def display_playerhand():
    for line_chess in player2_hand_map:
        for chess in line_chess:
            if chess:
                screen.blit(chess[0], chess[1])

    for line_chess in player1_hand_map:
        for chess in line_chess:
            if chess:
                screen.blit(chess[0], chess[1])
    
def show_promote(screen):
    """阻塞式弹窗，等待用户选择"""
    
    while True:
        hand = client.update_playerhand()
        opponenthand = client.update_opponenthand()
        screen.fill(WHITE)
        screen.blit(chessboard_image, [75,75])
        display_chessboard()
        display_playerhand()
        # 绘制弹窗
        pygame.draw.rect(game_surface, GRAY, (700, 300, 200, 200))
        draw_text("Promote?", 740, 320, WHITE)
        pygame.draw.rect(game_surface, GREEN, (720, 420, 65, 50))
        pygame.draw.rect(game_surface, RED, (815, 420, 65, 50))
        draw_text("Yes", 730, 430, BLACK)
        draw_text("No", 828, 430, BLACK)
        if client.role == '1':
            draw_titletext(client.opponent, 340, 700, RED)
            draw_titletext(username_input, 340, 10, BLUE)
            x_offset = 715
            y_offset = 580
            for piece, count in opponenthand.items():
                draw_titletext(f"{count}" ,x_offset, y_offset)
                x_offset += 60
                if x_offset >= 880 and y_offset != 680:
                    x_offset = 715
                    y_offset += 100
            
            x_offset = 715
            y_offset = 20 
            for piece, count in hand.items():
                draw_titletext(f"{count}" ,x_offset, y_offset)
                x_offset += 60
                if x_offset >= 940:
                    x_offset = 715
                    y_offset += 100
        elif client.role == '2':
            draw_titletext(client.opponent, 340, 10, RED)
            draw_titletext(username_input, 340, 700, BLUE)
            x_offset = 715
            y_offset = 580
            for piece, count in hand.items():
                draw_titletext(f"{count}" ,x_offset, y_offset)
                x_offset += 60
                if x_offset >= 880 and y_offset != 680:
                    x_offset = 715
                    y_offset += 100
            
            x_offset = 715
            y_offset = 20 
            for piece, count in opponenthand.items():
                draw_titletext(f"{count}" ,x_offset, y_offset)
                x_offset += 60
                if x_offset >= 940:
                    x_offset = 715
                    y_offset += 100
        pygame.display.update()
        
        # 事件处理
        for need_promote in pygame.event.get():
            if need_promote.type == pygame.QUIT:
                client.stop()
                send_request("logout", username_input, password_input)
                pygame.quit()
                exit()
            elif need_promote.type == pygame.MOUSEBUTTONDOWN:
                choose_x, choose_y = need_promote.pos
                if  720 <= choose_x <= 785 and 420 <= choose_y <= 470:
                    return True
                elif 815 <= choose_x <= 880 and 420 <= choose_y <= 470: 
                    return False

threading.Thread(target = receive_onlinePeopleAccounts, daemon=True).start()
threading.Thread(target = receive_neededPeopleAccounts, daemon=True).start()

running = True
while running:
    
    screen.blit(background_image, [0,0])
    clock = pygame.time.Clock()
    # 檢查事件
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            pygame.quit()
            exit()
        elif event.type == pygame.KEYDOWN:
            if active_input == "username":
                if event.key == pygame.K_BACKSPACE:
                    username_input = username_input[:-1]
                elif len(username_input) >= 25:
                    response = {'status': 'error', 'message': 'username reach limit'}
                    message = response['message']
                else:
                    username_input += event.unicode
            elif active_input == "password":
                if event.key == pygame.K_BACKSPACE:
                    password_input = password_input[:-1]
                else:
                    password_input += event.unicode
        elif event.type == pygame.MOUSEBUTTONDOWN:
            x, y = event.pos
            # 點擊判斷輸入框
            if 190 <= x <= 610 and 185 <= y <= 235:
                active_input = "username"
            elif 190 <= x <= 610 and 315 <= y <= 365:
                active_input = "password"
            else:
                active_input = ""
            
            # 點擊判斷按鈕
            if 190 <= x <= 375 and 400 <= y <= 450:
                response = send_request("register", username_input, password_input)
                message = response['message']
            elif 425 <= x <= 610 and 400 <= y <= 450:
                    response = send_request("login", username_input, password_input)
                    message = response['message']
                    if response['status'] == 'success':
                        client = GameClient(username_input)
                        logged_in = True
                        home_size = (800, 600)
                        home_surface = pygame.display.set_mode(home_size)
                        Home = True
                        
                        while Home:
                            home_surface.fill(WHITE)
                            onlinePeopleAccounts = receive_onlinePeopleAccounts()
                            neededPeopleAccounts = receive_neededPeopleAccounts()
                            for event in pygame.event.get():
                                if event.type == pygame.QUIT:
                                    response = send_request("logout", username_input, password_input)
                                    pygame.quit()
                                    exit()
                                elif event.type == pygame.MOUSEBUTTONDOWN:
                                    x, y = event.pos
                                    if 300 <= x <= 500 and 500 <= y <= 550:
                                        response = send_request("logout", username_input, password_input)
                                        client.stop()
                                        logged_in = False
                                        Home = False
                                    elif 200 <= x <= 600 and 250 <= y <= 350:
                                        if client.matching:
                                            client.cancel_matchmaking()  
                                        else:
                                            print("開始配對...")
                                            client.start_matchmaking()  

                            if client.opponent and client.role and client.game_id:
                                client.start_game()
                                game_size = (1000, 750)
                                game_surface = pygame.display.set_mode(game_size)
                                GAME = True
                                game_end = False
                                time.sleep(1)
                                while GAME:
                                    if game_end:
                                        GAME = False
                                        home_size = (800, 600)
                                        home_surface = pygame.display.set_mode(home_size)
                                        break
                                    client.start_game()
                                    playerTurn = client.update_playerTurn()
                                    chessboard_map = client.update_chessboard()
                                    hand = client.update_playerhand()
                                    opponenthand = client.update_opponenthand()
                                    who_win = client.update_who_win()
                                    game_surface.fill(WHITE)
                                    screen.blit(chessboard_image, [75,75])
                                    display_chessboard()
                                    display_playerhand()
                                    if who_win == "win":
                                        win_size = (400, 150)
                                        win_surface = pygame.display.set_mode(win_size)
                                        WIN = True
                                        while WIN:
                                            win_surface.fill(WHITE)
                                            time.sleep(0.1)
                                            for event in pygame.event.get():
                                                if event.type == pygame.QUIT:
                                                    response = send_request("logout", username_input, password_input)
                                                    client.stop()
                                                    pygame.quit()
                                                    exit()
                                                elif event.type == pygame.MOUSEBUTTONDOWN:
                                                    x, y = event.pos
                                                    if 175 <= x <= 225 and 90 <= y <= 120:
                                                        client.stop()
                                                        game_end = True
                                                        WIN = False
                                                        
                                            draw_titletext("Your Win!", 100, 10, GREEN)
                                            pygame.draw.rect(home_surface, BLACK, (165, 90, 70, 30))
                                            draw_text("OK", 177, 95, WHITE)
                                            pygame.display.update()
                                    elif who_win == "lose":
                                        lose_size = (400, 150)
                                        lose_surface = pygame.display.set_mode(lose_size)
                                        LOSE = True
                                        while LOSE:
                                            lose_surface.fill(WHITE)
                                            time.sleep(0.1)
                                            for event in pygame.event.get():
                                                if event.type == pygame.QUIT:
                                                    response = send_request("logout", username_input, password_input)
                                                    client.stop()
                                                    pygame.quit()
                                                    exit()
                                                elif event.type == pygame.MOUSEBUTTONDOWN:
                                                    x, y = event.pos
                                                    if 175 <= x <= 225 and 90 <= y <= 120:
                                                        client.stop()
                                                        game_end = True
                                                        LOSE = False
                                                        
                                            draw_titletext("Your Lose", 95, 10, RED)
                                            pygame.draw.rect(home_surface, BLACK, (165, 90, 70, 30))
                                            draw_text("OK", 177, 95, WHITE)
                                            pygame.display.update()
                                    time.sleep(0.1)
                                    for event in pygame.event.get():

                                        if playerTurn != str(client.role):
                                            is_selected_chess = False
                                            selected_chess = None
                                            is_choosed_placechess = False
                                            choosed_placechess = None

                                        if event.type == pygame.QUIT:
                                            server.end(3 - int(client.role), client.game_id)
                                            response = send_request("logout", username_input, password_input)
                                            pygame.quit()
                                            exit()
                                        elif event.type == pygame.MOUSEBUTTONDOWN:
                                            x, y = event.pos
                                            if 100 <= x <= 640 and 100 <= y <= 640:
                                                x = int((x-100)/60)  
                                                y = int((y-100)/60)
                                                if chessboard_map[y][x] != None:
                                                    if is_selected_chess :
                                                        if server.is_legal_move(client.role, (prex,prey), (x,y), client.game_id):
                                                            if server.can_promote((prex,prey), y, client.game_id):
                                                                result_promote = show_promote(game_surface) 
                                                                if result_promote:
                                                                    server.promote(client.game_id, (prex,prey))
                                                                    result = server.move(client.role, (prex, prey), (x, y), client.game_id)
                                                                    if result == "winner":
                                                                        server.end(client.role, client.game_id)
                                                                    elif result == "checkmate":
                                                                        server.end(3 - client.role, client.game_id)
                                                                        print(f"玩家 {3 - client.role} 赢了!")
                                                                    elif result:
                                                                        if server.checkmate(client.game_id, str(3 - int(client.role))):
                                                                            server.end(client.role, client.game_id)
                                                                            print(f"玩家 {client.role} 赢了!")
                                                                            
                                                                    is_selected_chess = False
                                                                    selected_chess = None
                                                                else: 
                                                                    result = server.move(client.role, (prex, prey), (x, y), client.game_id)
                                                                    if result == "winner":
                                                                        server.end(client.role, client.game_id)
                                                                    elif result == "checkmate":
                                                                        server.end(3 - client.role, client.game_id)
                                                                        print(f"玩家 {3 - client.role} 赢了!")
                                                                    elif result:
                                                                        if server.checkmate(client.game_id, str(3 - int(client.role))):
                                                                            server.end(client.role, client.game_id)
                                                                            print(f"玩家 {client.role} 赢了!")

                                                                    is_selected_chess = False
                                                                    selected_chess = None
                                                            else:
                                                                result = server.move(client.role, (prex, prey), (x, y), client.game_id)
                                                                if result == "winner":
                                                                    server.end(client.role, client.game_id)
                                                                elif result == "checkmate":
                                                                    server.end(3 - client.role, client.game_id)
                                                                    print(f"玩家 {3 - client.role} 赢了!")
                                                                elif result:
                                                                    if server.checkmate(client.game_id, str(3 - int(client.role))):
                                                                        server.end(client.role, client.game_id)
                                                                        print(f"玩家 {client.role} 赢了!")

                                                                is_selected_chess = False
                                                                selected_chess = None
                                                        else:
                                                            is_selected_chess = False
                                                            selected_chess = None
                                                    else:
                                                        selected_chess = chessboard_map[y][x]
                                                        is_selected_chess = True
                                                        is_choosed_placechess = False
                                                        choosed_placechess = None
                                                else:
                                                    if is_selected_chess:
                                                        if server.is_legal_move(client.role, (prex,prey), (x,y), client.game_id):
                                                            if server.can_promote((prex,prey), y, client.game_id):
                                                                result_promote = show_promote(game_surface)  
                                                                if result_promote:
                                                                    promote = False
                                                                    server.promote(client.game_id, (prex,prey))
                                                                    result = server.move(client.role, (prex, prey), (x, y), client.game_id)
                                                                    if result == "winner":
                                                                        server.end(client.role, client.game_id)
                                                                    elif result == "checkmate":
                                                                        server.end(3 - client.role, client.game_id)
                                                                        print(f"玩家 {3 - client.role} 赢了!")
                                                                    elif result:
                                                                        if server.checkmate(client.game_id, str(3 - int(client.role))):
                                                                            server.end(client.role, client.game_id)
                                                                            print(f"玩家 {client.role} 赢了!")

                                                                    is_selected_chess = False
                                                                    selected_chess = None
                                                                else: 
                                                                    promote = False
                                                                    result = server.move(client.role, (prex, prey), (x, y), client.game_id)
                                                                    if result == "winner":
                                                                        server.end(client.role, client.game_id)
                                                                    elif result == "checkmate":
                                                                        server.end(3 - client.role, client.game_id)
                                                                        print(f"玩家 {3 - client.role} 赢了!")
                                                                    elif result:
                                                                        if server.checkmate(client.game_id, str(3 - int(client.role))):
                                                                            server.end(client.role, client.game_id)
                                                                            print(f"玩家 {client.role} 赢了!")

                                                                    is_selected_chess = False
                                                                    selected_chess = None
                                                            else:
                                                                result = server.move(client.role, (prex, prey), (x, y), client.game_id)
                                                                if result == "winner":
                                                                    server.end(client.role, client.game_id)
                                                                elif result == "checkmate":
                                                                    server.end(3 - client.role, client.game_id)
                                                                    print(f"玩家 {3 - client.role} 赢了!")
                                                                elif result:
                                                                    if server.checkmate(client.game_id, str(3 - int(client.role))):
                                                                        server.end(client.role, client.game_id)
                                                                        print(f"玩家 {client.role} 赢了!")
                                                                is_selected_chess = False
                                                                selected_chess = None
                                                        else:
                                                            is_selected_chess = False
                                                            selected_chess = None
                                                    elif is_choosed_placechess:
                                                        if server.can_place_piece(client.game_id, client.role, choosed_placechess, (x, y)):
                                                            server.place(client.role, client.game_id, (x, y), choosed_placechess)
                                                        is_choosed_placechess = False
                                                        choosed_placechess = None
                                                prex = x
                                                prey = y
                                            elif 700 <= x <= 880 and 520 <= y <= 580:
                                                x = int((x - 700) /60)
                                                is_choosed_placechess = True
                                                is_selected_chess = False
                                                selected_chess = None
                                                if x == 0:
                                                    choosed_placechess = "B_2" 
                                                elif x == 1:
                                                    choosed_placechess = "R_2"
                                                elif x == 2:
                                                    choosed_placechess = "P_2"
                                            elif 700 <= x <= 940 and 620 <= y <= 680:
                                                x = int((x - 700) /60)
                                                is_choosed_placechess = True
                                                is_selected_chess = False
                                                selected_chess = None
                                                if x == 0:
                                                    choosed_placechess = "L_2" 
                                                elif x == 1:
                                                    choosed_placechess = "N_2"
                                                elif x == 2:
                                                    choosed_placechess = "S_2"
                                                elif x == 3:
                                                    choosed_placechess = "G_2"
                                            elif 700 <= x <= 940 and 60 <= y <= 120:
                                                x = int((x - 700) /60)
                                                is_choosed_placechess = True
                                                is_selected_chess = False
                                                selected_chess = None
                                                if x == 0:
                                                    choosed_placechess = "L_1" 
                                                elif x == 1:
                                                    choosed_placechess = "N_1"
                                                elif x == 2:
                                                    choosed_placechess = "S_1"
                                                elif x == 3:
                                                    choosed_placechess = "G_1"
                                            elif 700 <= x <= 880 and 160 <= y <= 220:
                                                x = int((x - 700) /60)
                                                is_choosed_placechess = True
                                                is_selected_chess = False
                                                selected_chess = None
                                                if x == 0:
                                                    choosed_placechess = "B_1" 
                                                elif x == 1:
                                                    choosed_placechess = "R_1"
                                                elif x == 2:
                                                    choosed_placechess = "P_1" 
                                    
                                    draw_titletext("Your" if playerTurn == str(client.role) else "Opponent", 700, 300, BLACK)
                                    draw_titletext("Turn", 700, 400, BLACK)
                                    if client.role == playerTurn and choosed_placechess != None or client.role == playerTurn and selected_chess != None:
                                        if choosed_placechess != None:
                                            draw_text("place:", 800, 360)
                                            screen.blit(pygame.image.load("image/" + choosed_placechess + ".png"), (910, 345))
                                        elif selected_chess != None:
                                            draw_text("choose:", 800, 360)
                                            screen.blit(selected_chess[0], (910,345))
                                    if client.role == '1':
                                        draw_titletext(client.opponent, 340, 700, RED)
                                        draw_titletext(username_input, 340, 10, GREEN)
                                        x_offset = 715
                                        y_offset = 580
                                        for piece, count in opponenthand.items():
                                            draw_titletext(f"{count}" ,x_offset, y_offset)
                                            x_offset += 60
                                            if x_offset >= 880 and y_offset != 680:
                                                x_offset = 715
                                                y_offset += 100
                                        
                                        x_offset = 715
                                        y_offset = 20 
                                        for piece, count in hand.items():
                                            draw_titletext(f"{count}" ,x_offset, y_offset)
                                            x_offset += 60
                                            if x_offset >= 940:
                                                x_offset = 715
                                                y_offset += 100
                                    
                                    elif client.role == '2':
                                        draw_titletext(client.opponent, 340, 10, RED)
                                        draw_titletext(username_input, 340, 700, GREEN)
                                        x_offset = 715
                                        y_offset = 580
                                        for piece, count in hand.items():
                                            draw_titletext(f"{count}" ,x_offset, y_offset)
                                            x_offset += 60
                                            if x_offset >= 880 and y_offset != 680:
                                                x_offset = 715
                                                y_offset += 100
                                        
                                        x_offset = 715
                                        y_offset = 20 
                                        for piece, count in opponenthand.items():
                                            draw_titletext(f"{count}" ,x_offset, y_offset)
                                            x_offset += 60
                                            if x_offset >= 940:
                                                x_offset = 715
                                                y_offset += 100
                                    
                                    pygame.display.update()

                            draw_titletext(f"Online User Accounnts: {onlinePeopleAccounts}", 100, 50, BLACK)
                            draw_titletext(f"needed User Accounnts: {neededPeopleAccounts}", 100, 150, RED)  
                            pygame.draw.rect(home_surface, RED if client.matching == True else GREEN, (200, 250, 400, 100))
                            draw_titletext(" waiting..." if client.matching == True else "start queue", 280, 275, BLACK)
                            pygame.draw.rect(home_surface, BLACK, (300, 500, 200, 50))
                            draw_text("Logout", 350, 515, WHITE)
                            pygame.display.update()   
                            
                                
                                 


    # 繪製輸入框和文字
    pygame.draw.rect(screen, RED if active_input == "username" else BLUE, (190, 185, 420, 50))
    pygame.draw.rect(screen, RED if active_input == "password" else BLUE, (190, 315, 420, 50))
    
    draw_gametitletext("Japanese    Shogi", 210, 50)
    draw_titletext("Username", 280, 120)
    draw_text(username_input, 200, 197)
    draw_titletext("Password", 290, 250)
    draw_text("*" * len(password_input), 200, 335)
    
    # 繪製按鈕
    pygame.draw.rect(screen, BLACK, (190, 400, 185, 50))
    pygame.draw.rect(screen, BLACK, (425, 400, 185, 50))
    draw_text("Register", 225, 415, WHITE)
    draw_text("Login", 475, 415, WHITE)
    
    # 顯示訊息
    if "successful" not in message:
        draw_text(message, 50, 550, RED)
    pygame.display.update()

pygame.quit()
