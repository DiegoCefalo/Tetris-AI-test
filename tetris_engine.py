# Modified from Tetromino by lusob luis@sobrecueva.com
# http://lusob.com
# Released under a "Simplified BSD" license

import random, time, pygame, sys
from pygame.locals import *
import numpy as np
import torch
import copy

FPS = 25
BOXSIZE = 20
BOARDWIDTH = 10
BOARDHEIGHT = 20
WINDOWWIDTH = 640
WINDOWHEIGHT = 480
BLANK = '.'

MOVESIDEWAYSFREQ = 0.15
MOVEDOWNFREQ = 0.1

XMARGIN = int((WINDOWWIDTH - BOARDWIDTH * BOXSIZE) / 2)
TOPMARGIN = WINDOWHEIGHT - (BOARDHEIGHT * BOXSIZE) - 5

#               R    G    B
WHITE       = (255, 255, 255)
GRAY        = (185, 185, 185)
BLACK       = (  0,   0,   0)
RED         = (155,   0,   0)
LIGHTRED    = (175,  20,  20)
GREEN       = (  0, 155,   0)
LIGHTGREEN  = ( 20, 175,  20)
BLUE        = (  0,   0, 155)
LIGHTBLUE   = ( 20,  20, 175)
YELLOW      = (155, 155,   0)
LIGHTYELLOW = (175, 175,  20)

BORDERCOLOR = BLUE
BGCOLOR = BLACK
TEXTCOLOR = WHITE
TEXTSHADOWCOLOR = GRAY
COLORS      = (     BLUE,      GREEN,      RED,      YELLOW)
LIGHTCOLORS = (LIGHTBLUE, LIGHTGREEN, LIGHTRED, LIGHTYELLOW)
assert len(COLORS) == len(LIGHTCOLORS) # each color must have light color

TEMPLATEWIDTH = 5
TEMPLATEHEIGHT = 5

S_SHAPE_TEMPLATE = [['..OO.',
                     '.OO..',
                     '.....',
                     '.....',
                     '.....'],
                    ['..O..',
                     '..OO.',
                     '...O.',
                     '.....',
                     '.....']]

Z_SHAPE_TEMPLATE = [['.OO..',
                     '..OO.',
                     '.....',
                     '.....',
                     '.....'],
                    ['..O..',
                     '.OO..',
                     '.O...',
                     '.....',
                     '.....']]

I_SHAPE_TEMPLATE = [['..O..',
                     '..O..',
                     '..O..',
                     '..O..',
                     '.....'],
                    ['.....',
                     'OOOO.',
                     '.....',
                     '.....',
                     '.....']]

O_SHAPE_TEMPLATE = [['.OO..',
                     '.OO..',
                     '.....',
                     '.....',
                     '.....']]

J_SHAPE_TEMPLATE = [['.O...',
                     '.OOO.',
                     '.....',
                     '.....',
                     '.....'],
                    ['..OO.',
                     '..O..',
                     '..O..',
                     '.....',
                     '.....'],
                    ['.OOO.',
                     '...O.',
                     '.....',
                     '.....',
                     '.....'],
                    ['..O..',
                     '..O..',
                     '.OO..',
                     '.....',
                     '.....']]

L_SHAPE_TEMPLATE = [['...O.',
                     '.OOO.',
                     '.....',
                     '.....',
                     '.....'],
                    ['..O..',
                     '..O..',
                     '..OO.',
                     '.....',
                     '.....'],
                    ['.OOO.',
                     '.O...',
                     '.....',
                     '.....',
                     '.....'],
                    ['.OO..',
                     '..O..',
                     '..O..',
                     '.....',
                     '.....']]

T_SHAPE_TEMPLATE = [['..O..',
                     '.OOO.',
                     '.....',
                     '.....',
                     '.....'],
                    ['..O..',
                     '..OO.',
                     '..O..',
                     '.....',
                     '.....'],
                    ['.OOO.',
                     '..O..',
                     '.....',
                     '.....',
                     '.....'],
                    ['..O..',
                     '.OO..',
                     '..O..',
                     '.....',
                     '.....']]

PIECES = {'S': S_SHAPE_TEMPLATE,
          'Z': Z_SHAPE_TEMPLATE,
          'J': J_SHAPE_TEMPLATE,
          'L': L_SHAPE_TEMPLATE,
          'I': I_SHAPE_TEMPLATE,
          'O': O_SHAPE_TEMPLATE,
          'T': T_SHAPE_TEMPLATE}

PIECES_NUM = {'S': 1,
          'Z': 2,
          'J': 3,
          'L': 4,
          'I': 5,
          'O': 6,
          'T': 7}


class GameState:
    def __init__(self):
        global FPSCLOCK, DISPLAYSURF, BASICFONT, BIGFONT
        pygame.init()
        FPSCLOCK = pygame.time.Clock()
        DISPLAYSURF = pygame.display.set_mode((WINDOWWIDTH, WINDOWHEIGHT))
        BASICFONT = pygame.font.Font('freesansbold.ttf', 18)
        BIGFONT = pygame.font.Font('freesansbold.ttf', 100)
        pygame.display.iconify()
        pygame.display.set_caption('Tetromino')

        # DEBUG
        self.total_lines = 0

        # setup variables for the start of the game
        self.board = self.getBlankBoard()
        self.lastMoveDownTime = time.time()
        self.lastMoveSidewaysTime = time.time()
        self.lastFallTime = time.time()
        self.movingDown = False # note: there is no movingUp variable
        self.movingLeft = False
        self.movingRight = False
        self.score = 0
        self.lines = 0
        self.height = 0
        self.level, self.fallFreq = self.calculateLevelAndFallFreq()

        self.fallingPiece = self.getNewPiece()
        self.nextPiece = self.getNewPiece()

        self.frame_step([1,0,0,0,0,0])

        pygame.display.update()

    def reinit(self):
        self.board = self.getBlankBoard()
        self.lastMoveDownTime = time.time()
        self.lastMoveSidewaysTime = time.time()
        self.lastFallTime = time.time()
        self.movingDown = False # note: there is no movingUp variable
        self.movingLeft = False
        self.movingRight = False
        self.score = 0
        self.lines = 0
        self.height = 0
        self.level, self.fallFreq = self.calculateLevelAndFallFreq()

        self.fallingPiece = self.getNewPiece()
        self.nextPiece = self.getNewPiece()

        self.frame_step([1,0,0,0,0,0])

        pygame.display.update()
        return torch.FloatTensor([0]*6)


    def frame_step(self,input,render=True):
        self.movingLeft = False
        self.movingRight = False

        reward = self.score
        terminal = False

        #none is 100000, left is 010000, up is 001000, right is 000100, space is 000010, q is 000001
        if self.fallingPiece == None:
            # No falling piece in play, so start a new piece at the top
            self.fallingPiece = self.nextPiece
            self.nextPiece = self.getNewPiece()
            self.lastFallTime = time.time() # reset self.lastFallTime

            if not self.isValidPosition():
                image_data = pygame.surfarray.array3d(pygame.display.get_surface())
                terminal = True

                self.reinit()
                return image_data, reward-50, terminal # can't fit a new piece on the self.board, so game over


        # moving the piece sideways
        if (input[1] == 1) and self.isValidPosition(adjX=-1):
            self.fallingPiece['x'] -= 1
            self.movingLeft = True
            self.movingRight = False
            self.lastMoveSidewaysTime = time.time()

        elif (input[3] == 1) and self.isValidPosition(adjX=1):
            self.fallingPiece['x'] += 1
            self.movingRight = True
            self.movingLeft = False
            self.lastMoveSidewaysTime = time.time()

        # rotating the piece (if there is room to rotate)
        elif (input[2] == 1):
            self.fallingPiece['rotation'] = (self.fallingPiece['rotation'] + 1) % len(PIECES[self.fallingPiece['shape']])
            if not self.isValidPosition():
                self.fallingPiece['rotation'] = (self.fallingPiece['rotation'] - 1) % len(PIECES[self.fallingPiece['shape']])

        elif (input[5] == 1): # rotate the other direction
            self.fallingPiece['rotation'] = (self.fallingPiece['rotation'] - 1) % len(PIECES[self.fallingPiece['shape']])
            if not self.isValidPosition():
                self.fallingPiece['rotation'] = (self.fallingPiece['rotation'] + 1) % len(PIECES[self.fallingPiece['shape']])

        # move the current piece all the way down
        elif (input[4] == 1):
            self.movingDown = False
            self.movingLeft = False
            self.movingRight = False
            for i in range(1, BOARDHEIGHT):
                if not self.isValidPosition(adjY=i):
                    break
            self.fallingPiece['y'] += i - 1

        # handle moving the piece because of user input
        # if (self.movingLeft or self.movingRight):
        #     if self.movingLeft and self.isValidPosition(adjX=-1):
        #         self.fallingPiece['x'] -= 1
        #     elif self.movingRight and self.isValidPosition(adjX=1):
        #         self.fallingPiece['x'] += 1
        #     self.lastMoveSidewaysTime = time.time()

        if self.movingDown:
            self.fallingPiece['y'] += 1
            self.lastMoveDownTime = time.time()

        # let the piece fall if it is time to fall
        # see if the piece has landed
        cleared = 0
        if not self.isValidPosition(adjY=1):
            # falling piece has landed, set it on the self.board
            self.addToBoard()

            cleared = self.removeCompleteLines()
            if cleared > 0:
                if cleared == 1:
                    self.score += 40 * self.level
                elif cleared == 2:
                    self.score += 100 * self.level
                elif cleared == 3:
                    self.score += 300 * self.level
                elif cleared == 4:
                    self.score += 1200 * self.level

            self.score += 1

            self.lines += cleared
            self.total_lines += cleared

            reward = self.score 
            #- self._number_of_holes(self.board) - self._bumpiness(self.board) - self._height(self.board) - self._blocksAboveHoles(self.board)
            
            self.height = self.getHeight()

            self.level, self.fallFreq = self.calculateLevelAndFallFreq()
            self.fallingPiece = None

        else:
            # piece did not land, just move the piece down
            self.fallingPiece['y'] += 1

        # drawing everything on the screen
        if render:
            DISPLAYSURF.fill(BGCOLOR)
            self.drawBoard()
            self.drawStatus()
            self.drawNextPiece()
            if self.fallingPiece != None:
                self.drawPiece(self.fallingPiece)

            pygame.display.update()

        # if cleared > 0:
        #     reward = 100 * cleared
            
        if self.fallingPiece == None:
            # No falling piece in play, so start a new piece at the top
            self.fallingPiece = self.nextPiece
            self.nextPiece = self.getNewPiece()
            self.lastFallTime = time.time() # reset self.lastFallTime
            
            if not self.isValidPosition():
                image_data = pygame.surfarray.array3d(pygame.display.get_surface())
                terminal = True

                self.reinit()
                return image_data, reward-50, terminal # can't fit a new piece on the self.board, so game over

        image_data = pygame.surfarray.array3d(pygame.display.get_surface())
        return image_data, reward, terminal

    def getImage(self):
        image_data = pygame.surfarray.array3d(pygame.transform.rotate(pygame.display.get_surface(), 90))
        return image_data

    def getActionSet(self):
        return range(6)

    def getHeight(self):
        stack_height = 0
        for i in range(0, BOARDHEIGHT):
            blank_row = True
            for j in range(0, BOARDWIDTH):
                if self.board[j][i] != '.':
                    blank_row = False
            if not blank_row:
                stack_height = BOARDHEIGHT - i
                break
        return stack_height

    def getReward(self):
        stack_height = None
        num_blocks = 0
        for i in range(0, BOARDHEIGHT):
            blank_row = True
            for j in range(0, BOARDWIDTH):
                if self.board[j][i] != '.':
                    num_blocks += 1
                    blank_row = False
            if not blank_row and stack_height is None:
                stack_height = BOARDHEIGHT - i

        if stack_height is None:
            return BOARDHEIGHT
        else:
            return BOARDHEIGHT - stack_height
            return float(num_blocks) / float(stack_height * BOARDWIDTH)

    def isGameOver(self):
        return self.fallingPiece == None and not self.isValidPosition()

    def makeTextObjs(self,text, font, color):
        surf = font.render(text, True, color)
        return surf, surf.get_rect()

    def calculateLevelAndFallFreq(self):
        # Based on the self.score, return the self.level the player is on and
        # how many seconds pass until a falling piece falls one space.
        self.level = min(int(self.lines / 10) + 1, 10)
        self.fallFreq = 0.27 - (self.level * 0.02)
        return self.level, self.fallFreq

    def getNewPiece(self):
        # return a random new piece in a random rotation and color
        shape = random.choice(list(PIECES.keys()))
        newPiece = {'shape': shape,
                    'rotation': random.randint(0, len(PIECES[shape]) - 1),
                    'x': int(BOARDWIDTH / 2) - int(TEMPLATEWIDTH / 2),
                    'y': 0, # start it above the self.board (i.e. less than 0)
                    'color': random.randint(0, len(COLORS)-1)}
        return newPiece


    def addToBoard(self):
        # fill in the self.board based on piece's location, shape, and rotation
        for x in range(TEMPLATEWIDTH):
            for y in range(TEMPLATEHEIGHT):
                if PIECES[self.fallingPiece['shape']][self.fallingPiece['rotation']][y][x] != BLANK:
                    self.board[x + self.fallingPiece['x']][y + self.fallingPiece['y']] = self.fallingPiece['color']
                    
    def sim_addToBoard(self, board, fallingPiece):
        # fill in the board based on piece's location, shape, and rotation
        sim_board = []
        sim_piece = {}
        sim_piece.update(zip(fallingPiece.keys(),fallingPiece.values()))
        for x in board:
            sim_board.append(x)
        for x in range(TEMPLATEWIDTH):
            for y in range(TEMPLATEHEIGHT):
                if PIECES[sim_piece['shape']][sim_piece['rotation']][y][x] != BLANK:
                    sim_board[x + sim_piece['x']][y + sim_piece['y']] = sim_piece['color']
        return sim_board


    def getBlankBoard(self):
        # create and return a new blank self.board data structure
        self.board = []
        for i in range(BOARDWIDTH):
            self.board.append([BLANK] * BOARDHEIGHT)
        return self.board


    def isOnBoard(self,x, y):
        return x >= 0 and x < BOARDWIDTH and y < BOARDHEIGHT


    def isValidPosition(self,adjX=0, adjY=0, action=0):
        # Return True if the piece is within the self.board and not colliding
        for x in range(TEMPLATEWIDTH):
            for y in range(TEMPLATEHEIGHT):
                isAboveBoard = y + self.fallingPiece['y'] + adjY < 0
                if isAboveBoard or PIECES[self.fallingPiece['shape']][self.fallingPiece['rotation']][y][x] == BLANK:
                    continue
                if not self.isOnBoard(x + self.fallingPiece['x'] + adjX, y + self.fallingPiece['y'] + adjY):
                    return False
                if self.board[x + self.fallingPiece['x'] + adjX][y + self.fallingPiece['y'] + adjY] != BLANK:
                    return False
                # if self.board[x + action][y + self.fallingPiece['y'] + adjY] != BLANK:
                #     return False
        return True
    
    def simisValidPosition(self, board, piece, adjX=0, adjY=0):
        # Return True if the piece is within the board and not colliding
        for x in range(TEMPLATEWIDTH):
            for y in range(TEMPLATEHEIGHT):
                isAboveBoard = y + piece['y'] + adjY < 0
                if isAboveBoard or PIECES[piece['shape']][piece['rotation']][y][x] == BLANK:
                    continue
                if not self.isOnBoard(x + piece['x'] + adjX, y + piece['y'] + adjY):
                    return False
                if board[x + piece['x'] + adjX][y + piece['y'] + adjY] != BLANK:
                    return False
        return True

    def isCompleteLine(self, y):
        # Return True if the line filled with boxes with no gaps.
        for x in range(BOARDWIDTH):
            if self.board[x][y] == BLANK:
                return False
        return True
    def simisCompleteLine(self,board, y):
        # Return True if the line filled with boxes with no gaps.
        for x in range(BOARDWIDTH):
            if board[x][y] == BLANK:
                return False
        return True


    def removeCompleteLines(self):
        # Remove any completed lines on the self.board, move everything above them down, and return the number of complete lines.
        numLinesRemoved = 0
        y = BOARDHEIGHT - 1 # start y at the bottom of the self.board
        while y >= 0:
            if self.isCompleteLine(y):
                # Remove the line and pull boxes down by one line.
                for pullDownY in range(y, 0, -1):
                    for x in range(BOARDWIDTH):
                        self.board[x][pullDownY] = self.board[x][pullDownY-1]
                # Set very top line to blank.
                for x in range(BOARDWIDTH):
                    self.board[x][0] = BLANK
                numLinesRemoved += 1
                # Note on the next iteration of the loop, y is the same.
                # This is so that if the line that was pulled down is also
                # complete, it will be removed.
            else:
                y -= 1 # move on to check next row up
        return numLinesRemoved
    
    def simremoveCompleteLines(self, board):
        # Remove any completed lines on the board, move everything above them down, and return the number of complete lines.
        numLinesRemoved = 0
        y = BOARDHEIGHT - 1 # start y at the bottom of the board
        while y >= 0:
            if self.simisCompleteLine(board, y):
                # Remove the line and pull boxes down by one line.
                for pullDownY in range(y, 0, -1):
                    for x in range(BOARDWIDTH):
                        board[x][pullDownY] = board[x][pullDownY-1]
                # Set very top line to blank.
                for x in range(BOARDWIDTH):
                    board[x][0] = BLANK
                numLinesRemoved += 1
                # Note on the next iteration of the loop, y is the same.
                # This is so that if the line that was pulled down is also
                # complete, it will be removed.
            else:
                y -= 1 # move on to check next row up
        return numLinesRemoved


    def convertToPixelCoords(self,boxx, boxy):
        # Convert the given xy coordinates of the self.board to xy
        # coordinates of the location on the screen.
        return (XMARGIN + (boxx * BOXSIZE)), (TOPMARGIN + (boxy * BOXSIZE))


    def drawBox(self,boxx, boxy, color, pixelx=None, pixely=None):
        # draw a single box (each tetromino piece has four boxes)
        # at xy coordinates on the self.board. Or, if pixelx & pixely
        # are specified, draw to the pixel coordinates stored in
        # pixelx & pixely (this is used for the "Next" piece).
        if color == BLANK:
            return
        if pixelx == None and pixely == None:
            pixelx, pixely = self.convertToPixelCoords(boxx, boxy)
        pygame.draw.rect(DISPLAYSURF, COLORS[color], (pixelx + 1, pixely + 1, BOXSIZE - 1, BOXSIZE - 1))
        pygame.draw.rect(DISPLAYSURF, LIGHTCOLORS[color], (pixelx + 1, pixely + 1, BOXSIZE - 4, BOXSIZE - 4))


    def drawBoard(self):
        # draw the border around the self.board
        pygame.draw.rect(DISPLAYSURF, BORDERCOLOR, (XMARGIN - 3, TOPMARGIN - 7, (BOARDWIDTH * BOXSIZE) + 8, (BOARDHEIGHT * BOXSIZE) + 8), 5)

        # fill the background of the self.board
        pygame.draw.rect(DISPLAYSURF, BGCOLOR, (XMARGIN, TOPMARGIN, BOXSIZE * BOARDWIDTH, BOXSIZE * BOARDHEIGHT))
        # draw the individual boxes on the self.board
        for x in range(BOARDWIDTH):
            for y in range(BOARDHEIGHT):
                self.drawBox(x, y, self.board[x][y])


    def drawStatus(self):
        # draw the self.score text
        scoreSurf = BASICFONT.render('score: %s' % self.score, True, TEXTCOLOR)
        scoreRect = scoreSurf.get_rect()
        scoreRect.topleft = (WINDOWWIDTH - 150, 20)
        DISPLAYSURF.blit(scoreSurf, scoreRect)

        # draw the self.level text
        levelSurf = BASICFONT.render('level: %s' % self.level, True, TEXTCOLOR)
        levelRect = levelSurf.get_rect()
        levelRect.topleft = (WINDOWWIDTH - 150, 50)
        DISPLAYSURF.blit(levelSurf, levelRect)


    def drawPiece(self,piece, pixelx=None, pixely=None):
        shapeToDraw = PIECES[piece['shape']][piece['rotation']]
        if pixelx == None and pixely == None:
            # if pixelx & pixely hasn't been specified, use the location stored in the piece data structure
            pixelx, pixely = self.convertToPixelCoords(piece['x'], piece['y'])

        # draw each of the boxes that make up the piece
        for x in range(TEMPLATEWIDTH):
            for y in range(TEMPLATEHEIGHT):
                if shapeToDraw[y][x] != BLANK:
                    self.drawBox(None, None, piece['color'], pixelx + (x * BOXSIZE), pixely + (y * BOXSIZE))


    def drawNextPiece(self):
        # draw the "next" text
        nextSurf = BASICFONT.render('Next:', True, TEXTCOLOR)
        nextRect = nextSurf.get_rect()
        nextRect.topleft = (WINDOWWIDTH - 120, 80)
        DISPLAYSURF.blit(nextSurf, nextRect)
        # draw the "next" piece
        self.drawPiece(self.nextPiece,pixelx=WINDOWWIDTH-120, pixely=100)

    def get_next_states(self):
        '''Get all possible next states'''
        states = {}
        piece_id = self.fallingPiece['shape']
        sim_piece = {}
        sim_piece.update(zip(self.fallingPiece.keys(),self.fallingPiece.values()))
        if piece_id == 'O': 
            rotations = [0]
        elif piece_id in ['I','S','Z']:
            rotations = [0,1]
        else:
            rotations = [0, 1, 2, 3]

        # For all rotations
        for rotation in rotations:
            sim_piece['rotation'] = rotation

            if (sim_piece['shape'] == 'J' and  sim_piece['rotation'] == 1) \
            or (sim_piece['shape'] == 'I' and  sim_piece['rotation'] == 0) \
            or (sim_piece['shape'] == 'S' and  sim_piece['rotation'] == 1) \
            or (sim_piece['shape'] == 'T' and  sim_piece['rotation'] == 1) \
            or (sim_piece['shape'] == 'L' and  sim_piece['rotation'] == 1):
                range_ = range(-2, BOARDWIDTH - self.piecewidth(PIECES[self.fallingPiece['shape']][rotation])-1)
            elif (sim_piece['shape'] == 'I' and  sim_piece['rotation'] == 1):
                range_ = range(0, BOARDWIDTH - self.piecewidth(PIECES[self.fallingPiece['shape']][rotation])+1)
            else:
                range_ = range(-1, BOARDWIDTH - self.piecewidth(PIECES[self.fallingPiece['shape']][rotation]))
            # For all positions
            for position in range_:
                sim_piece['x'] = position
                sim_piece['y'] = 0
                #Drop piece
                while self.simisValidPosition(self.board, sim_piece):
                    sim_piece['y'] += 1
                sim_piece['y'] -= 1

                # Valid move

                sim_board = [[x for x in y] for y in self.board]
                sim_board = self.sim_addToBoard(sim_board, sim_piece)
                states[(position, rotation)] = torch.FloatTensor([self.simremoveCompleteLines(sim_board) , self._number_of_holes(sim_board), self._bumpiness(sim_board), self._height(sim_board),PIECES_NUM[self.fallingPiece['shape']],PIECES_NUM[self.nextPiece['shape']]])#, self._blocksAboveHoles(sim_board)  + self._board_to_num(sim_board)
                # , self._blocksAboveHoles(sim_board)
                a = np.array(sim_board)

                sim_board = [[x for x in y] for y in self.board]
                
                

                # print(a.transpose())
                # print(states)


        return states

    def piecewidth(self, piece):
        minwidth=5
        maxwidth=0
        for x in piece:
            if 'O' in x:
                a = x.index('O')
                b = max([i if x == "O" else 0 for i, x in enumerate(x)])
                if a < minwidth:
                    minwidth = a
                if b > maxwidth:
                    maxwidth = b
        return  maxwidth - minwidth + 1

    def get_state_size(self):
        '''Size of the state'''
        return 4

    def _number_of_holes(self, board):
        '''Number of holes in the board (empty sqquare with at least one block above it)'''
        holes = 0

        for col in board:
            i = 0
            while i < BOARDHEIGHT and col[i] == BLANK:
                i += 1
            holes += len([x for x in col[i+1:] if x == BLANK])

        return holes

    def _height(self, board):
        '''Sum and maximum height of the board'''
        sum_height = 0
        max_height = 0
        min_height = BOARDHEIGHT

        for col in board:
            i = 0
            while i < BOARDHEIGHT and col[i] == BLANK:
                i += 1
            height = BOARDHEIGHT - i
            sum_height += height
            if height > max_height:
                max_height = height
            elif height < min_height:
                min_height = height

        return sum_height

    def _bumpiness(self, board):
        '''Sum of the differences of heights between pair of columns'''
        total_bumpiness = 0
        max_bumpiness = 0
        min_ys = []

        for col in board:
            i = 0
            while i < BOARDHEIGHT and col[i] == BLANK:
                i += 1
            min_ys.append(i)

        for i in range(len(min_ys) - 1):
            bumpiness = abs(min_ys[i] - min_ys[i+1])
            max_bumpiness = max(bumpiness, max_bumpiness)
            total_bumpiness += abs(min_ys[i] - min_ys[i+1])


        return total_bumpiness
    
    def _blocksAboveHoles(self,board):
        count = 0
        justonce  =0
        for col in board:
            for ind,x in enumerate(col[::-1]):
                if x == BLANK:
                    try:
                        if col[::-1][ind+1] != BLANK and justonce < 1:
                            for y in col[::-1][ind:]:
                                if y != BLANK:
                                    count += 1
                    except:
                        continue
        return count
    
    def _board_to_num(self,board):
        board_copy = copy.deepcopy(board)
        for ind1,col in enumerate(board_copy):
            for ind2,x in enumerate(col[::-1]):
                if x == BLANK:
                    board_copy[ind1][ind2] = 0
                else:
                    board_copy[ind1][ind2] = 1
        return np.array(board_copy).flatten().tolist()