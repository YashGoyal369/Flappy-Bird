import sys, time, random, pygame
from collections import deque
import cv2 as cv, mediapipe as mp
from pygame import mixer
mp_drawing = mp.solutions.drawing_utils
mp_drawing_styles = mp.solutions.drawing_styles
mp_face_mesh = mp.solutions.face_mesh
drawing_spec = mp_drawing.DrawingSpec(thickness=1, circle_radius=1)
pygame.init()

#background music
mixer.music.load("mu.mp3")
mixer.music.play(-1)

# Initialize required elements/environment
VID_CAP = cv.VideoCapture(0)
window_size =(800,600)
screen = pygame.display.set_mode(window_size)

# Bird and pipe init
# Calculate scaling factor based on the new screen size and original screen size
scaling_factor = window_size[0] / VID_CAP.get(cv.CAP_PROP_FRAME_WIDTH)
bird_img = pygame.image.load("bird_sprite.png")
bird_img = pygame.transform.scale(bird_img, (int(bird_img.get_width() / 6 * scaling_factor), int(bird_img.get_height() / 6 * scaling_factor)))
bird_frame = bird_img.get_rect()
bird_frame.center = (window_size[0] // 6, window_size[1] // 2)
pipe_frames = deque()
pipe_img = pygame.image.load("pipe_sprite_single.png")

# Calculate the scaled dimensions of the pipe
pipe_img = pygame.transform.scale(pipe_img, (int(pipe_img.get_width() * scaling_factor), int(pipe_img.get_height() * scaling_factor)))
pipe_starting_template = pipe_img.get_rect()
space_between_pipes = int(200 * scaling_factor)  # Adjust as needed

#highscore
high_score=0

try:
    with open("high_score.txt", "r") as file:
        high_score = int(file.read())
except FileNotFoundError:
    # If the file doesn't exist (first-time play), the high score remains 0
    high_score = 0
except Exception as e:
    print(f"Error loading high score: {e}")

# Game loop
game_clock = time.time()
stage = 1
pipeSpawnTimer = 0
time_between_pipe_spawn = 40
dist_between_pipes = 500
pipe_velocity = lambda: dist_between_pipes / time_between_pipe_spawn
level = 0
score = 0
didUpdateScore = False
game_is_running = True

with mp_face_mesh.FaceMesh(
        max_num_faces=1,
        refine_landmarks=True,
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5) as face_mesh:
    while True:
        # Check if game is running
        if not game_is_running:
            text = pygame.font.SysFont("Helvetica Bold.ttf", 64).render('Game over!', True, (99, 245, 255))
            tr = text.get_rect()
            tr.center = (window_size[0]/2, window_size[1]/2)
            screen.blit(text, tr)
            pygame.display.update()
            pygame.time.wait(2000)
            VID_CAP.release()
            cv.destroyAllWindows()
            pygame.quit()
            sys.exit()

        # Check if user quit window
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                VID_CAP.release()
                cv.destroyAllWindows()
                pygame.quit()
                sys.exit()

        # Get frame
        ret, frame = VID_CAP.read()
        if not ret:
            print("Empty frame, continuing...")
            continue
        # Ensure that the dimensions are integers and match the screen dimensions
        window_width, window_height = window_size
        frame = cv.resize(frame, (int(window_width), int(window_height)))

        
        # Clear screen
        screen.fill((125, 220, 232))

        # Face mesh
        frame.flags.writeable = False
        frame = cv.cvtColor(frame, cv.COLOR_BGR2RGB)
        results = face_mesh.process(frame)
        frame.flags.writeable = True

        # Draw mesh
        if results.multi_face_landmarks and len(results.multi_face_landmarks) > 0:
            # 94 = Tip of nose
            marker = results.multi_face_landmarks[0].landmark[94].y
            bird_frame.centery = (marker - 0.5) * 1.5 * window_size[1] + window_size[1]/2
            if bird_frame.top < 0: bird_frame.y = 0
            if bird_frame.bottom > window_size[1]: bird_frame.y = window_size[1] - bird_frame.height

        # Mirror frame, swap axes because opencv != pygame
        frame = cv.flip(frame, 1).swapaxes(0, 1)

        # Update pipe positions using the scaling factor
        for pf in pipe_frames:
            pf[0].x -= int(pipe_velocity() * scaling_factor)
            pf[1].x -= int(pipe_velocity() * scaling_factor)
    

        if len(pipe_frames) > 0 and pipe_frames[0][0].right < 0:
            pipe_frames.popleft()

        # Update screen
        pygame.surfarray.blit_array(screen, frame)
        screen.blit(bird_img, bird_frame)
        checker = True
        for pf in pipe_frames:
            # Check if bird went through to update score
            if pf[0].left <= bird_frame.x <= pf[0].right:
                checker = False
                if not didUpdateScore:
                    score += 1
                    didUpdateScore = True
                    if score > high_score:
                        high_score = score
            # Update screen
            screen.blit(pipe_img, pf[1])
            screen.blit(pygame.transform.flip(pipe_img, 0, 1), pf[0])
        if checker: didUpdateScore = False

        # Stage, score text - adjust positions based on the new screen size
        text = pygame.font.SysFont("Helvetica Bold.ttf", int(50 * scaling_factor)).render(f'Stage {stage}', True, (99, 245, 255))
        tr = text.get_rect()
        tr.center = (int(100 * scaling_factor), int(20 * scaling_factor))
        screen.blit(text, tr)

        high_score_text = pygame.font.SysFont("Helvetica Bold.ttf", int(50 * scaling_factor)).render(f'High Score: {high_score}', True, (99, 245, 255))
        tr = high_score_text.get_rect()
        tr.center = (int(120 * scaling_factor), int(60 * scaling_factor))
        screen.blit(high_score_text, tr)

        
        text = pygame.font.SysFont("Helvetica Bold.ttf", int(50 * scaling_factor)).render(f'Score: {score}', True, (99, 245, 255))
        tr = text.get_rect()
        tr.center = (int(100 * scaling_factor), int(100 * scaling_factor))
        screen.blit(text, tr)

        # Update screen
        pygame.display.flip()

        # Check if bird is touching a pipe
        if any([bird_frame.colliderect(pf[0]) or bird_frame.colliderect(pf[1]) for pf in pipe_frames]):
            game_is_running = False
            with open("high_score.txt","w") as f:
                f.write(str(high_score))

        # Time to add new pipes
        if pipeSpawnTimer == 0:
            top = pipe_starting_template.copy()
            min_y = 50  # Adjust this value as needed
            max_y = window_size[1] - space_between_pipes - 50  # Adjust this value as needed
            space_height = random.randint(min_y, max_y)
            top.x, top.y = window_size[0], space_height - pipe_starting_template.height
            bottom = pipe_starting_template.copy()
            bottom.x, bottom.y = window_size[0], space_height + space_between_pipes

            pipe_frames.append([top, bottom])

        # Update pipe spawn timer - make it cyclical
        pipeSpawnTimer += 1
        if pipeSpawnTimer >= time_between_pipe_spawn: pipeSpawnTimer = 0

        # Update stage
        if time.time() - game_clock >= 10:
            time_between_pipe_spawn *= 5 / 6
            stage += 1
            game_clock = time.time()
