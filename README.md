# go-game-python
"""
Простейшая консольная реализация игры ГО на Python.
Поддерживает:
- Размер доски (по умолчанию 9x9, можно указать 13 или 19)
- Ходы двух игроков (черные 'B' и белые 'W')
- Правила захвата (группы, свободы)
- Простая защита от кохэ (ko) — запрещает вернуться к предыдущему положению доски
- Pass и resign
- Подсчёт очков: камни + территория (флуд-филл пустых областей, если область окружена только одним цветом,
  то она присуждается этому цвету)

Ограничения / упрощения:
- Нет поддержки коми (можно легко добавить)
- Нет AI — игра для двух людей в консоли
- Ko-правило реализовано только как сравнение с последним состоянием (не длинная история)

Запуск: python go_game.py
"""

from copy import deepcopy

class GoGame:
    EMPTY = '.'
    BLACK = 'B'
    WHITE = 'W'

    def __init__(self, size=9):
        assert size in (9, 13, 19) or (size >= 5 and size <= 25), "Рекомендуемые размеры: 9, 13, 19"
        self.size = size
        self.board = [[self.EMPTY for _ in range(size)] for _ in range(size)]
        self.to_move = self.BLACK
        self.captured = {self.BLACK: 0, self.WHITE: 0}
        self.previous_board = None  # для простого ko
        self.passes = 0

    def copy_board(self):
        return tuple(''.join(row) for row in self.board)

    def display(self):
        # Печать координат
        header = '   ' + ' '.join(chr(ord('A') + i + (1 if i >= 8 else 0)) for i in range(self.size))
        # (Пропускаем букву 'I' чтобы удобнее читать, принятная в Go нотация)
        print(header)
        for r in range(self.size):
            row_num = self.size - r
            print(f"{row_num:2d}", ' '.join(self.board[r]), f"{row_num:2d}")
        print(header)
        print(f"Следующий ход: {'Чёрные' if self.to_move==self.BLACK else 'Белые'}")
        print(f"Захвачено: Чёрные={self.captured[self.BLACK]}, Белые={self.captured[self.WHITE]}")

    def in_bounds(self, r, c):
        return 0 <= r < self.size and 0 <= c < self.size

    def neighbors(self, r, c):
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = r+dr, c+dc
            if self.in_bounds(nr, nc):
                yield nr, nc

    def get_group(self, r, c, visited=None):
        if visited is None:
            visited = set()
        color = self.board[r][c]
        stack = [(r,c)]
        group = set()
        while stack:
            x,y = stack.pop()
            if (x,y) in group:
                continue
            group.add((x,y))
            for nx, ny in self.neighbors(x,y):
                if self.board[nx][ny] == color and (nx,ny) not in group:
                    stack.append((nx,ny))
        return group

    def liberties(self, group):
        libs = set()
        for (r,c) in group:
            for nr,nc in self.neighbors(r,c):
                if self.board[nr][nc] == self.EMPTY:
                    libs.add((nr,nc))
        return libs

    def remove_group(self, group):
        if not group:
            return 0
        color = self.board[next(iter(group))[0]][next(iter(group))[1]]
        for r,c in group:
            self.board[r][c] = self.EMPTY
        return len(group)

    def is_valid_move(self, r, c, color):
        if not self.in_bounds(r,c):
            return False, 'Выход за границы доски'
        if self.board[r][c] != self.EMPTY:
            return False, 'Клетка не пуста'
        # Создадим временную доску чтобы проверить самопат
        tmp = deepcopy(self.board)
        tmp[r][c] = color
        # удаляем вражеские группы без свобод
        enemy = self.BLACK if color == self.WHITE else self.WHITE
        to_remove = []
        for nr,nc in self.neighbors(r,c):
            if tmp[nr][nc] == enemy:
                grp = self._get_group_on_board(tmp, nr, nc)
                if not self._liberties_on_board(tmp, grp):
                    to_remove.append(grp)
        for grp in to_remove:
            for x,y in grp:
                tmp[x][y] = self.EMPTY
        # теперь проверим свободы своей группы
        grp_self = self._get_group_on_board(tmp, r, c)
        if not self._liberties_on_board(tmp, grp_self):
            return False, 'Ход самопроигрышный (suicide)'
        # ko: не позволяем вернуться в предыдущее состояние
        tmp_repr = tuple(''.join(row) for row in tmp)
        if self.previous_board is not None and tmp_repr == self.previous_board:
            return False, 'Запрещён ход из-за ko (повтор предыдущей позиции)'
        return True, ''

    def _get_group_on_board(self, board, r, c):
        color = board[r][c]
        stack = [(r,c)]
        group = set()
        while stack:
            x,y = stack.pop()
            if (x,y) in group:
                continue
            group.add((x,y))
            for nx, ny in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                if 0 <= nx < self.size and 0 <= ny < self.size and board[nx][ny] == color:
                    stack.append((nx,ny))
        return group

    def _liberties_on_board(self, board, group):
        for (r,c) in group:
            for nr,nc in ((r+1,c),(r-1,c),(r,c+1),(r,c-1)):
                if 0 <= nr < self.size and 0 <= nc < self.size and board[nr][nc] == self.EMPTY:
                    return True
        return False

    def play_move(self, r, c):
        color = self.to_move
        valid, reason = self.is_valid_move(r,c,color)
        if not valid:
            return False, reason
        # Сохраняем доску для ko-проверки
        self.previous_board = self.copy_board()
        # ставим камень
        self.board[r][c] = color
        # удаляем вражеские группы без свобод
        enemy = self.BLACK if color == self.WHITE else self.WHITE
        total_captured = 0
        for nr,nc in list(self.neighbors(r,c)):
            if self.board[nr][nc] == enemy:
                grp = self.get_group(nr,nc)
                if not self.liberties(grp):
                    removed = self.remove_group(grp)
                    total_captured += removed
        self.captured[color] += total_captured
        # переключаем очередь
        self.to_move = enemy
        self.passes = 0
        return True, ''

    def pass_move(self):
        self.previous_board = self.copy_board()
        self.passes += 1
        self.to_move = self.BLACK if self.to_move == self.WHITE else self.WHITE

    def resign(self):
        winner = self.WHITE if self.to_move == self.BLACK else self.BLACK
        return winner

    def score(self):
        # Простое подсчитывание: камни + территория
        stones = {self.BLACK:0, self.WHITE:0}
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] == self.BLACK:
                    stones[self.BLACK] += 1
                elif self.board[r][c] == self.WHITE:
                    stones[self.WHITE] += 1
        territory = {self.BLACK:0, self.WHITE:0}
        visited = set()
        for r in range(self.size):
            for c in range(self.size):
                if self.board[r][c] != self.EMPTY or (r,c) in visited:
                    continue
                # flood fill пустой региона
                queue = [(r,c)]
                region = set()
                bordering = set()
                while queue:
                    x,y = queue.pop()
                    if (x,y) in region:
                        continue
                    region.add((x,y))
                    for nx,ny in self.neighbors(x,y):
                        if self.board[nx][ny] == self.EMPTY and (nx,ny) not in region:
                            queue.append((nx,ny))
                        elif self.board[nx][ny] in (self.BLACK, self.WHITE):
                            bordering.add(self.board[nx][ny])
                visited |= region
                if len(bordering) == 1:
                    owner = next(iter(bordering))
                    territory[owner] += len(region)
        final = {self.BLACK: stones[self.BLACK]+territory[self.BLACK],
                 self.WHITE: stones[self.WHITE]+territory[self.WHITE]}
        return {
            'stones': stones,
            'territory': territory,
            'final': final,
        }


def parse_coord(s, size):
    # Ожидается: буква+число, буква латинская без I (I пропущена)
    s = s.strip().upper()
    if s == 'PASS':
        return 'PASS'
    if s == 'RESIGN':
        return 'RESIGN'
    # отделим буквы и цифры
    import re
    m = re.match(r"^([A-Z]+)([0-9]+)$", s)
    if not m:
        return None
    col_s, row_s = m.groups()
    # Обрабатываем колонку: учитываем пропуск 'I'
    col = 0
    for ch in col_s:
        if ch == 'I':
            return None
        if ch > 'Z' or ch < 'A':
            return None
        val = ord(ch) - ord('A')
        if ch > 'I':
            val -= 1
        col = col*26 + val
    try:
        row = int(row_s)
    except:
        return None
    # convert to 0-indexed matrix coords
    r = size - row
    c = col
    if r < 0 or r >= size or c < 0 or c >= size:
        return None
    return r, c


def human_play_loop(size=9):
    game = GoGame(size=size)
    print(f"Запуск игры GO {size}x{size}. Ходы: введите координату (например D4), PASS, или RESIGN.")
    while True:
        game.display()
        if game.passes >= 2:
            print('Оба игрока пасовали подряд — игра закончена. Подсчёт очков.')
            break
        player = 'Чёрные' if game.to_move==game.BLACK else 'Белые'
        s = input(f"{player} ({game.to_move}) ход: ").strip()
        parsed = parse_coord(s, game.size)
        if parsed is None:
            print('Неверный ввод, попробуйте ещё раз. Формат: A1, D4, PASS, RESIGN')
            continue
        if parsed == 'PASS':
            game.pass_move()
            continue
        if parsed == 'RESIGN':
            winner = game.resign()
            print(f"{winner} победил (сдача).")
            return
        r,c = parsed
        ok, reason = game.play_move(r,c)
        if not ok:
            print('Невалидный ход:', reason)
            continue
    result = game.score()
    print('Камни:', result['stones'])
    print('Территория:', result['territory'])
    print('Итог:', result['final'])
    if result['final'][game.BLACK] > result['final'][game.WHITE]:
        print('Победили Чёрные')
    elif result['final'][game.WHITE] > result['final'][game.BLACK]:
        print('Победили Белые')
    else:
        print('Ничья')


if __name__ == '__main__':
    try:
        s = input('Размер доски (enter для 9, или 9/13/19): ').strip()
        size = int(s) if s else 9
    except Exception:
        size = 9
    human_play_loop(size)
