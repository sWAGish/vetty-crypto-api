
from datetime import datetime, timedelta
from typing import Optional, List, Dict

import requests
from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel

COINGECKO_API_URL = "https://api.coingecko.com/api/v3"
API_USERNAME = "admin"
API_PASSWORD = "admin123"
SECRET_KEY = "CHANGE_THIS_SECRET_KEY_TO_SOMETHING_RANDOM"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

app = FastAPI(
    title="Vetty Crypto Market API",
    version="1.0.0",
    description="Simple API that fetches cryptocurrency data from CoinGecko, protected with JWT.",
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str


def authenticate_user(username: str, password: str) -> Optional[User]:
    if username == API_USERNAME and password == API_PASSWORD:
        return User(username=username)
    return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta is None:
        expires_delta = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    if username != API_USERNAME:
        raise credentials_exception

    return User(username=username)


@app.post("/auth/token", response_model=Token, tags=["auth"])
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> Token:
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = create_access_token({"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


def call_coingecko(path: str, params: Optional[Dict] = None) -> list:
    url = f"{COINGECKO_API_URL}{path}"
    try:
        response = requests.get(url, params=params, timeout=10)
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error while calling CoinGecko: {exc}",
        ) from exc

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"CoinGecko returned status code {response.status_code}",
        )

    return response.json()


@app.get("/coins", tags=["coins"])
def list_coins(
    page_num: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=250),
    current_user: User = Depends(get_current_user),
):
    all_coins = call_coingecko("/coins/list")

    total_items = len(all_coins)
    start_index = (page_num - 1) * per_page
    end_index = start_index + per_page
    page_items = all_coins[start_index:end_index]

    return {
        "page_num": page_num,
        "per_page": per_page,
        "total_items": total_items,
        "items": page_items,
    }


@app.get("/categories", tags=["categories"])
def list_categories(
    page_num: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=250),
    current_user: User = Depends(get_current_user),
):
    all_categories = call_coingecko("/coins/categories/list")

    total_items = len(all_categories)
    start_index = (page_num - 1) * per_page
    end_index = start_index + per_page
    page_items = all_categories[start_index:end_index]

    return {
        "page_num": page_num,
        "per_page": per_page,
        "total_items": total_items,
        "items": page_items,
    }


@app.get("/markets", tags=["markets"])
def list_markets(
    coin_ids: Optional[str] = Query(
        default=None,
        description="Comma separated list of coin ids, e.g. bitcoin,ethereum",
    ),
    category_id: Optional[str] = Query(
        default=None, description="Category id from the /categories endpoint."
    ),
    page_num: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=250),
    current_user: User = Depends(get_current_user),
):
    if not coin_ids and not category_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must provide coin_ids and/or category_id.",
        )

    ids_list: Optional[List[str]] = None
    if coin_ids:
        ids_list = [c.strip() for c in coin_ids.split(",") if c.strip()]

    base_params = {
        "order": "market_cap_desc",
        "per_page": 250,
        "page": 1,
        "sparkline": "false",
    }

    params_inr = base_params.copy()
    params_inr["vs_currency"] = "inr"

    params_cad = base_params.copy()
    params_cad["vs_currency"] = "cad"

    if ids_list:
        joined_ids = ",".join(ids_list)
        params_inr["ids"] = joined_ids
        params_cad["ids"] = joined_ids

    if category_id:
        params_inr["category"] = category_id
        params_cad["category"] = category_id

    inr_data = call_coingecko("/coins/markets", params_inr)
    cad_data = call_coingecko("/coins/markets", params_cad)

    cad_index: Dict[str, dict] = {coin["id"]: coin for coin in cad_data}

    merged: List[dict] = []
    for coin in inr_data:
        cid = coin["id"]
        cad_coin = cad_index.get(cid)

        entry = {
            "id": cid,
            "symbol": coin.get("symbol"),
            "name": coin.get("name"),
            "inr": {
                "price": coin.get("current_price"),
                "market_cap": coin.get("market_cap"),
                "price_change_percentage_24h": coin.get(
                    "price_change_percentage_24h"
                ),
            },
            "cad": {
                "price": cad_coin.get("current_price") if cad_coin else None,
                "market_cap": cad_coin.get("market_cap") if cad_coin else None,
                "price_change_percentage_24h": cad_coin.get(
                    "price_change_percentage_24h"
                )
                if cad_coin
                else None,
            },
        }
        merged.append(entry)

    total_items = len(merged)
    start_index = (page_num - 1) * per_page
    end_index = start_index + per_page
    page_items = merged[start_index:end_index]

    return {
        "page_num": page_num,
        "per_page": per_page,
        "total_items": total_items,
        "items": page_items,
    }
