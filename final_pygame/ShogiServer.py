from xmlrpc.server import SimpleXMLRPCServer
from socketserver import ThreadingMixIn
import json
import os
import threading
import uuid

# 記錄已登入的使用者
logged_in_users = {}
lock = threading.Lock()

# 使用者資料檔案
USER_DATA_FILE = "users.json"

# 讀取使用者資料
def read_users():
    if os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "r") as file:
            return json.load(file)
    return {}

# 寫入使用者資料
def write_users(users):
    with open(USER_DATA_FILE, "w") as file:
        json.dump(users, file)

# 註冊功能
def register(username, password):
    if not username or not password:
        return {'status': 'error', 'message': 'Missing username or password'}

    users = read_users()

    if username in users:
        return {'status': 'error', 'message': 'Username already exists'}

    # 將新使用者存入 JSON 檔案
    users[username] = {'password': password}
    write_users(users)

    return {'status': 'success', 'message': 'Registration successful'}

# 登入功能
def login(username, password):
    if not username or not password:
        return {'status': 'error', 'message': 'Missing username or password'}

    users = read_users()

    if username not in users or users[username]['password'] != password:
        return {'status': 'error', 'message': 'Invalid username or password'}

    if username in logged_in_users:
        return {'status': 'error', 'message': 'User already login'}
    # 紀錄登入的使用者
    logged_in_users[username] = True
    return {'status': 'success', 'message': 'Login successful'}

# 登出功能
def logout(username):
    if username in logged_in_users:
        del logged_in_users[username]  # 移除使用者的登入狀態
        return {'status': 'success', 'message': 'Logout successful'}
    else:
        return {'status': 'error', 'message': 'User not logged in'}

# 抓取線上人數
def onlinePeopleAccounts():
    return len(logged_in_users)

class MatchmakingServer:
    def __init__(self):
        self.queue = []
        self.lock = threading.Lock()
        self.matches = {}  # 存儲配對結果
        self.games = {}
        self.gameid = 0

    def join_queue(self, client_name):
        with self.lock:
            if client_name in self.matches:  # 已完成配對
                return self.matches.pop(client_name)

            if client_name in self.queue:  # 已在佇列中
                return []
            # 加入佇列
            self.queue.append(client_name)
            if len(self.queue) >= 2:
                client1 = self.queue.pop(0)
                client2 = self.queue.pop(0)
                self.gameid += 1
                self.games[self.gameid] = {
                    "1": client1,
                    "2": client2
                }
                self.matches[client1] = {"role": "1", "game_id": self.gameid, "oppoenet": client2}
                self.matches[client2] = {"role": "2", "game_id": self.gameid, "oppoenet": client1}
                print(f"配對成功：{client1} 和 {client2}")
                return self.matches.pop(client_name)
        return []

    def leave_queue(self, client_name):
        with self.lock:
            if client_name in self.queue:
                self.queue.remove(client_name)
                print(f"{client_name} 已取消配對")
                return True
        return False
    
    def remove_after_match(self, client_name):
        with self.lock:
            if client_name in self.matches:
                # 找到對手，移除雙方的配對關係
                opponent = self.matches.pop(client_name)
                if opponent in self.matches:
                    self.matches.pop(opponent)
                print(f"配對移除：{client_name} 和 {opponent}")
                return True
        return False
    
    def neededPeopleAccounts(self):
        return 2 - len(self.queue)

class Game:

    def __init__(self):
        self.chessboard = [[None] * 9 for _ in range(9)]
        self.player_hands = {'1': {'L_1': 0, 'N_1': 0, 'S_1': 0, 'G_1': 0, 'B_1': 0, 'R_1': 0, 'P_1': 0}, '2': {'B_2': 0, 'R_2': 0, 'P_2': 0, 'L_2': 0, 'N_2': 0, 'S_2': 0, 'G_2': 0}} 
        self.playerwin = None
        self.playerturn = '1'
        self.gameturn = {}
        self.games = {}
        self.game_player_hands = {}
        self.game_end = {}
        self.setup_pieces()

    def setup_pieces(self):
        self.chessboard[0] = ["L_1", "N_1", "S_1", "G_1", "K_1", "G_1", "S_1", "N_1", "L_1"]
        self.chessboard[1] = [ None, "R_1",  None,  None,  None,  None,  None, "B_1",  None]
        self.chessboard[2] = ["P_1", "P_1", "P_1", "P_1", "P_1", "P_1", "P_1", "P_1", "P_1"]
        self.chessboard[6] = ["P_2", "P_2", "P_2", "P_2", "P_2", "P_2", "P_2", "P_2", "P_2"]
        self.chessboard[7] = [ None, "B_2",  None,  None,  None,  None,  None, "R_2",  None]
        self.chessboard[8] = ["L_2", "N_2", "S_2", "G_2", "K_2", "G_2", "S_2", "N_2", "L_2"]

    def newgame(self, gameid):
        self.chessboard = [[None] * 9 for _ in range(9)]
        self.setup_pieces()
        self.games.update({gameid: self.chessboard})
        self.gameturn.update({gameid: self.playerturn})
        self.game_player_hands.update({gameid: self.player_hands})
        self.game_end.update({gameid: self.playerwin})

    def update_board(self, gameid):
        return self.games[gameid]
    
    def update_turn(self, gameid):
        return self.gameturn[gameid]

    def update_playerhand(self, player, gameid):
        return self.game_player_hands[gameid][player]
    
    def update_oppoenethand(self, player, gameid):
        return self.game_player_hands[gameid][str(3 - int(player))]

    def can_promote(self, startpos, to_y, gameid):
        start_x, start_y = startpos
        piece = self.games[gameid][start_y][start_x]
        if piece.split('_')[0] in ['P', 'L', 'N', 'S', 'R', 'B']:
            if piece.split('_')[1] == '1' and to_y >= 6:
                return True
            elif piece.split('_')[1] == '2' and to_y <= 2:
                return True
            else:
                return False
        return False

    def promote(self, gameid, startpos):
        start_x, start_y = startpos
        piece = self.games[gameid][start_y][start_x]

        if piece ==  "P_1":
            piece = "PP_1"
        elif piece == "L_1":
            piece = "LP_1"
        elif piece == "N_1":
            piece = "NP_1"
        elif piece == "S_1":
            piece = "SP_1"
        elif piece == "R_1":
            piece = "RP_1"
        elif piece == "B_1":
            piece = "BP_1"
        elif piece ==  "P_2":
            piece = "PP_2"
        elif piece == "L_2":
            piece = "LP_2"
        elif piece == "N_2":
            piece = "NP_2"
        elif piece == "S_2":
            piece = "SP_2"
        elif piece == "R_2":
            piece = "RP_2"
        elif piece == "B_2":
            piece = "BP_2"

        self.games[gameid][start_y][start_x] = piece
        

    def piece_is_legal_move(self, piece, from_pos, to_pos, gameid):
        from_x, from_y = from_pos
        to_x, to_y = to_pos
        dx = to_x - from_x
        dy = to_y - from_y
        # 判断棋子的移动规则
        if piece == "K_1" or piece == "K_2": #王將 
            return abs(dx) <= 1 and abs(dy) <= 1
        elif piece == "G_1":  # 金将
                return (abs(dx) == 1 and dy == 0) or (abs(dx) <= 1 and dy == 1) or (dx == 0 and dy == -1)
        elif piece == "G_2":
                return (abs(dx) == 1 and dy == 0) or (abs(dx) <= 1 and dy == -1) or (dx == 0 and dy == 1)
        elif piece == "S_1":
            return (abs(dx) <= 1 and dy == 1) or (dx == 1 or dx == -1 and dy == -1)
        elif piece == "S_2":
            return (abs(dx) <= 1 and dy == -1) or (dx == 1 or dx == -1 and dy == 1)
        elif piece == "N_1":
            return ((dx == 1 or dx == -1) and dy == 2)
        elif piece == "N_2":
            return ((dx == 1 or dx == -1) and dy == -2) 
        elif piece == "L_1":
            return dx == 0 and dy > 0
        elif piece == "L_2":
            return dx == 0 and dy < 0
        elif piece == "P_1":
            return dx == 0 and dy == 1
        elif piece == "P_2":
            return dx == 0 and dy == -1
        elif piece == "R_1" or piece == "RP_1":
            if dx == 0 or dy == 0:  
                return self.is_clear_path(from_pos, to_pos, gameid)
            elif piece == "RP_1":
                return abs(dx) == 1 and abs(dy) == 1
        elif piece == "R_2" or piece == "RP_2":
            if dx == 0 or dy == 0:  
                return self.is_clear_path(from_pos, to_pos, gameid)  
            elif piece == "RP_2":
                return abs(dx) == 1 and abs(dy) == 1 
        elif piece == "B_1" or piece == "BP_1":
            if abs(dx) == abs(dy):  
                return self.is_clear_path(from_pos, to_pos, gameid)
            elif piece == "BP_1":
                return (dx == 0 and abs(dy) == 1) or (dy == 0 and abs(dx) == 1)
        elif piece == "B_2" or piece == "BP_2":
            if abs(dx) == abs(dy):  
                return self.is_clear_path(from_pos, to_pos, gameid)
            elif piece == "BP_2":
                return (dx == 0 and abs(dy) == 1) or (dy == 0 and abs(dx) == 1)
        return False
        
    def is_clear_path(self, from_pos, to_pos, gameid):
        # 检查在直线或对角线移动时路径是否被阻挡
        from_x, from_y = from_pos
        to_x, to_y = to_pos
        dx = to_x - from_x
        dy = to_y - from_y
        step_x = 0 if dx == 0 else (1 if dx > 0 else -1)
        step_y = 0 if dy == 0 else (1 if dy > 0 else -1)

        x, y = from_x + step_x, from_y + step_y
        while (x, y) != (to_x, to_y):
            if self.games[gameid][y][x] != None:
                return False  # 路径被阻挡
            x += step_x
            y += step_y
        return True
    
    def is_legal_move(self, player, startpos, endpos, gameid):
        from_x, from_y = startpos
        to_x, to_y = endpos
        piece = self.games[gameid][from_y][from_x]
        pieceplayer = piece.split('_')[1]
        if self.gameturn[gameid] != player:
            print("移動失敗:不是你的回合")
            return False
        
        if not piece != None or pieceplayer != player:
            print("移動失敗:不是你的棋子")
            return False 

        if self.games[gameid][to_y][to_x] != None and self.games[gameid][to_y][to_x].split('_')[1] == player:
            print("移動失敗:已經有我方的棋子")
            return False 

        return self.piece_is_legal_move(piece, startpos, endpos, gameid)
    
    def king_is_legal_move(self, player, startpos, endpos, gameid):
        from_x, from_y = startpos
        to_x, to_y = endpos
        piece = self.games[gameid][from_y][from_x]
        pieceplayer = piece.split('_')[1]
        
        if not piece != None or pieceplayer != player:
            print("移動失敗:不是你的棋子")
            return False 

        if self.games[gameid][to_y][to_x] != None and self.games[gameid][to_y][to_x].split('_')[1] == player:
            print("移動失敗:已經有我方的棋子")
            return False 

        return self.piece_is_legal_move(piece, startpos, endpos, gameid)
    
    def is_under_attack(self, gameid,player, pos):
        x, y = pos
        for opponent in ['1', '2']:
            if opponent != player:
                for row in range(9):
                    for col in range(9):
                        if self.games[gameid][row][col] != None:
                            piece = self.games[gameid][row][col]
                            pieceplayer = piece.split('_')[1]
                            if pieceplayer == opponent:
                                if self.piece_is_legal_move(piece, (col, row), (x, y), gameid):
                                    return True
        return False
    
    def king_is_under_attack(self, gameid ,player, pos, startpos):
        x, y = pos
        from_x, from_y = startpos
        kingpiece = self.games[gameid][from_y][from_x] 
        self.games[gameid][from_y][from_x] = None
        for opponent in ['1', '2']:
            if opponent != player:
                for row in range(9):
                    for col in range(9):
                        if self.games[gameid][row][col] != None:
                            piece = self.games[gameid][row][col]
                            pieceplayer = piece.split('_')[1]
                            if pieceplayer == opponent:
                                if self.piece_is_legal_move(piece, (col, row), (x, y), gameid):
                                    self.games[gameid][from_y][from_x] = kingpiece
                                    return True
        self.games[gameid][from_y][from_x] = kingpiece                    
        return False

    def is_king_in_check(self, gameid ,player):
        king_pos = None
        # 查找玩家的王将或玉将位置
        for row in range(9):
            for col in range(9):
                if self.games[gameid][row][col] != None:
                    piece = self.games[gameid][row][col]
                    pieceplayer = piece.split('_')[1]
                    if (piece.split('_')[0] == 'K') and pieceplayer == player:
                        king_pos = (col, row)
                        break
        return self.is_under_attack(gameid ,player, king_pos)

    def find_attacking_pieces(self, gameid, player, king_pos):
        attackers = []
        x, y = king_pos
        kingpiece = self.games[gameid][y][x] 
        self.games[gameid][y][x] = None
        for row in range(9):
            for col in range(9):
                if self.games[gameid][row][col] != None:
                    piece = self.games[gameid][row][col]
                    pieceplayer = piece.split('_')[1]
                    if pieceplayer != player:
                        if self.piece_is_legal_move(piece, (col, row), (x, y), self.games[gameid]):
                            self.games[gameid][y][x] = kingpiece
                            attackers.append((piece, (col, row)))
        self.games[gameid][y][x] = kingpiece                
        return attackers
    
    def can_place_piece(self, gameid ,player, piece_name, pos):
        x, y = pos
        if self.gameturn[gameid] != player:
            print("不是你的回合")
            return False
        
        if not (0 <= x < 9 and 0 <= y < 9):
            print("位置無效")
            return False

        if self.games[gameid][y][x] != None:
            print("該位置已被佔用")
            return False

        if piece_name.split('_')[0] == "P" and any(
            self.games[gameid][row][x] != None and
            self.games[gameid][row][x].split('_')[0] == "P" and
            self.games[gameid][row][x].split('_')[1] == player
            for row in range(9)
        ):
            print("該列已經有步兵，不能再放置")
            return False
        
        if player == 1:
            if piece_name.split('_')[0] == 'P' and y == 8:
                print("步兵放在這無法行走，不能放置")
                return False
            elif piece_name.split('_')[0] == 'N' and y >= 7:
                print("桂馬放在這無法行走，不能放置")
                return False    
            elif piece_name.split('_')[0] == 'L' and y == 8:
                print("香車放在這無法行走，不能放置")
                return False   
        elif player == 2:  
            if piece_name.split('_')[0] == 'P' and y == 0:
                print("步兵放在這無法行走，不能放置")
                return False
            elif piece_name.split('_')[0] == 'N' and y <= 1:
                print("桂馬放在這無法行走，不能放置")
                return False    
            elif piece_name.split('_')[0] == 'L' and y == 0:
                print("香車放在這無法行走，不能放置")
                return False

        if piece_name.split('_')[0] == 'P':
            self.games[gameid][y][x] = piece_name
            if self.checkmate(gameid, str(3 - player)):
                self.games[gameid][y][x] = None      
                print("無法在王將前放下兵，將死")
                return False

        for piece in self.game_player_hands[gameid][player]:
            if piece == piece_name:
                return True

        print("持駒中没有该棋子")
        return False  

    def can_block_attack(self, gameid, player, king_pos, attacker_pos):
        attacker_x, attacker_y = attacker_pos
        king_x, king_y = king_pos
        piece = self.games[gameid][attacker_y][attacker_x]
        # 只處理飛車、角行和香車
        if piece.split('_')[0] not in ['R', 'B', 'L', 'RP', 'BP']:
            return False
        
        # 根據不同棋子的移動方式來計算攻擊路徑
        if piece.split('_')[0] == 'R' or piece.split('_')[0] == 'RP':  # 飛車的橫向和縱向攻擊路徑
            if attacker_x == king_x:  # 垂直方向
                path = [(attacker_x, y) for y in range(min(attacker_y, king_y) + 1, max(attacker_y, king_y))]
            elif attacker_y == king_y:  # 水平方向
                path = [(x, attacker_y) for x in range(min(attacker_x, king_x) + 1, max(attacker_x, king_x))]
            else:
                return False
        
        elif piece.split('_')[0] == 'B' or piece.split('_')[0] == 'BP':  # 角行的斜向攻擊路徑
            if abs(attacker_x - king_x) == abs(attacker_y - king_y):  # 確保在同一對角線
                dx = (king_x - attacker_x) // abs(king_x - attacker_x)
                dy = (king_y - attacker_y) // abs(king_y - attacker_y)
                path = [(attacker_x + i * dx, attacker_y + i * dy) for i in range(1, abs(king_x - attacker_x))]
            else:
                return False
        
        elif piece.split('_')[0] == "L":  # 香車的垂直攻擊路徑，只在同列
            if attacker_x == king_x and ((piece.split('_')[1] == 1 and attacker_y < king_y) or (piece.split('_')[1] == 2 and attacker_y > king_y)):
                if piece.split('_')[1] == '1':
                    path = [(attacker_x, y) for y in range(attacker_y + 1, king_y)]
                else:
                    path = [(attacker_x, y) for y in range(king_y + 1, attacker_y)]
            else:
                return False

        for piece in self.game_player_hands[gameid][player]:  
                for pos in path:
                    if self.can_place_piece(gameid, player, piece.split('_')[0], pos):
                        return True  # 找到可以放置的持駒  

        # 檢查玩家是否有棋子可以移動到攻擊路徑上
        for row in range(9):
            for col in range(9):
                if self.games[gameid][row][col] != None:
                    piece = self.games[gameid][row][col]
                    if piece.split('_')[1] == player and piece.split('_')[0] not in ["K"]:
                        if self.piece_is_legal_move(piece, (col, row), attacker_pos, gameid):
                                if self.is_under_attack(gameid, player, attacker_pos):
                                    return True
                    if piece.split('_')[1] == player and piece.split('_')[0] not in ["K"]:
                        for pos in path:
                            if self.piece_is_legal_move(piece, (col, row), pos, gameid):
                                self.games[gameid][row][col] = None
                                pos_x, pos_y = pos
                                self.games[gameid][pos_y][pos_x] = piece
                                if not self.is_under_attack(gameid, player, (king_x, king_y)):
                                    self.games[gameid][pos_y][pos_x] = None
                                    self.games[gameid][row][col] = piece
                                    return True   
                        
        return False

    def has_legal_moves_for_king(self, gameid, player):
        king_pos = None
        # 查找玩家的王将或玉将位置
        for row in range(9):
            for col in range(9):
                if self.games[gameid][row][col] != None:
                    piece = self.games[gameid][row][col]
                    if (piece.split('_')[0] == 'K')  and piece.split('_')[1] == player:
                        king_pos = (col, row)
                        break

        # 检查王将的周围位置是否有合法移动
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue  # 不检查当前位置
                new_x = king_pos[0] + dx
                new_y = king_pos[1] + dy
                if 0 <= new_x < 9 and 0 <= new_y < 9:
                    # 检查新位置是否合法
                    if self.king_is_legal_move(player, king_pos, (new_x, new_y),  gameid):
                        # 检查新位置是否受到攻击
                        if not self.king_is_under_attack(gameid, player, (new_x, new_y), (king_pos[0], king_pos[1])):
                            return True  # 找到合法移动   

        attackers = self.find_attacking_pieces(gameid, player, king_pos)
        for _, attacker_pos in attackers:
            if self.can_block_attack(gameid, player, king_pos, attacker_pos):
                return True  # 有其他棋子可以擋住攻擊

        return False  # 沒有合法移動或阻擋攻擊的方法

    def checkmate(self, gameid, player):
        if self.is_king_in_check(gameid, player) and not self.has_legal_moves_for_king(gameid, player):
            self.game_end[gameid] = 3 - int(player)
            print(f"玩家 {player} 被將死！")
            return True
        return False

    def checkmate_alarm(self, gameid, player):
        if self.is_king_in_check(gameid, player) and not self.has_legal_moves_for_king(gameid, player):
            print(f"玩家 {player} 被將死！")
            return True
        return False

    def move(self, player, startpos, endpos, gameid):

        from_x, from_y = startpos
        to_x, to_y = endpos
        piece = self.games[gameid][from_y][from_x]
        if piece != None and piece.split('_')[0] in ["K"] and self.king_is_under_attack(gameid, piece.split('_')[1], (to_x, to_y), (from_x, from_y)):
            print("移動失敗:移動後會受到攻擊")
            return False
        target_piece = self.games[gameid][to_y][to_x]
        if target_piece != None and target_piece.split('_')[0] == 'K':
            self.games[gameid][to_y][to_x] = piece
            self.games[gameid][from_y][from_x] = None
            print(f"玩家 {player} 赢了!")
            return "winner"
        if target_piece != None and target_piece.split('_')[1] != player:
            # 捕獲棋子，添加到持駒中
            parts = target_piece.split('_')
            parts[1] = player
            target_piece = '_'.join(parts)
            if  target_piece.split('_')[0] ==  "PP":
                parts = target_piece.split('_')
                parts[0] = 'P'  
                target_piece = '_'.join(parts)  
            elif  target_piece.split('_')[0] == "LP":
                parts = target_piece.split('_')
                parts[0] = 'L'  
                target_piece = '_'.join(parts) 
            elif  target_piece.split('_')[0] == "NP":
                parts = target_piece.split('_')
                parts[0] = 'N'  
                target_piece = '_'.join(parts)    
            elif  target_piece.split('_')[0] == "SP":
                parts = target_piece.split('_')
                parts[0] = 'S'  
                target_piece = '_'.join(parts) 
            elif  target_piece.split('_')[0] == "RP":
                parts = target_piece.split('_')
                parts[0] = 'R'  
                target_piece = '_'.join(parts) 
            elif  target_piece.split('_')[0] == "BP":
                parts = target_piece.split('_')
                parts[0] = 'B'  
                target_piece = '_'.join(parts) 
            self.game_player_hands[gameid][player][target_piece] += 1

        self.games[gameid][to_y][to_x] = piece
        self.games[gameid][from_y][from_x] = None

        if self.checkmate_alarm(gameid, player):
            print("無法移動，這樣會導致將死。")
            self.games[gameid][to_y][to_x] = None
            self.games[gameid][from_y][from_x] = piece
            return False
        if self.gameturn[gameid] == '1':
            self.gameturn[gameid] = '2'
        elif self.gameturn[gameid] == '2':
            self.gameturn[gameid] = '1'
        return True


    def place(self, player ,gameid, pos, piecename):
        x, y = pos        

        if self.game_player_hands[gameid][player][piecename] > 0:
            self.games[gameid][y][x] = piecename
            self.game_player_hands[gameid][player][piecename] -= 1
            print(f"玩家 {player} 放置 {piecename.split('_')[0]} 在 ({x}, {y})")
            if self.checkmate(gameid, str(3 - int(player))):
                return True
            if self.gameturn[gameid] == '1':
                self.gameturn[gameid] = '2'
            elif self.gameturn[gameid] == '2':
                self.gameturn[gameid] = '1'
            return True

        print("持駒中没有该棋子")
        return False
    
    def end(self, player ,gameid):
        self.game_end[gameid] = player

    def is_win(self, gameid):
        if self.game_end[gameid]:
            return self.game_end[gameid]
        return False


class MultiServer:
    def __init__(self):
        self.matchmaking_server = MatchmakingServer()
        self.game_server = Game()

    def _dispatch(self, method, params):
        if hasattr(self.matchmaking_server, method):
            return getattr(self.matchmaking_server, method)(*params)
        elif hasattr(self.game_server, method):
            return getattr(self.game_server, method)(*params)
        else:
            raise Exception(f"Method {method} not supported")


# 多執行緒伺服器設置
class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
    pass

# 啟動伺服器
server = ThreadedXMLRPCServer(("0.0.0.0", 12321),  allow_none=True)
print("Server started on port 12321...")

# 註冊函數
server.register_function(register, "register")
server.register_function(login, "login")
server.register_function(logout, "logout")
server.register_function(onlinePeopleAccounts)
server.register_instance(MultiServer())
try:
    server.serve_forever()
except KeyboardInterrupt:
    print("Server stopped.")
