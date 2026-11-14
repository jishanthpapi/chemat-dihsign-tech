from fastapi import FastAPI

app = FastAPI(title='CHEMa’t milestone 1')


@app.get('/health')
def health():
    return {'status': 'ok', 'milestone': 1, 'multiplayer_ready': False}
