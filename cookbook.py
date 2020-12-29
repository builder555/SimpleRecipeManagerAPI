from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from pydantic import BaseModel, Field, PrivateAttr, validator
from jsondb import ObjectStorage, PrimitiveStorage

app = FastAPI()

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecipeModel(BaseModel):
    url: str = Field(min_length=5)
    name: str = Field(min_length=5)
    ingredients: List[str]
    tags: List[str]
    __unmatched_ingredients: float = PrivateAttr()

    @property
    def match(self):
        return self.__unmatched_ingredients

    @validator('ingredients', 'tags')
    def convert_to_lowercase(cls, items):
        return [i.lower() for i in items]

    def compare_ingredients(self, ingredients):
        common_ingredients = set(ingredients) & set(self.ingredients)
        if common_ingredients:
            self.__unmatched_ingredients = (len(self.ingredients) - len(common_ingredients))
        else:
            self.__unmatched_ingredients = 10e5

    class Config:
        anystr_strip_whitespace = True


def get_recipes():
    return [RecipeModel(**r) for r in ObjectStorage('recipes').read()]


def save_recipe(recipe):
    ObjectStorage('recipes').create(recipe)


def search_recipes(ingredients):
    all_recp = get_recipes()
    ingredient_set = set([i.lower() for i in ingredients])
    for r in all_recp:
        r.compare_ingredients(ingredient_set)
    return sorted(all_recp, key=lambda r: r.match)


def get_ingredients():
    return PrimitiveStorage('ingredients').read()


def save_ingredients(new_entries):
    PrimitiveStorage('ingredients').create(new_entries)


@app.get('/recipes', response_model=List[RecipeModel])
def get_a_page_of_recipes():
    return get_recipes()


@app.get('/recipes/search')
def search_recipes_by_ingredient(ingredients: List[str] = Query([])):
    return search_recipes(ingredients)


@app.post('/recipes')
def add_new_recipe(recipe: RecipeModel):
    save_recipe(recipe.dict())
    save_ingredients(recipe.ingredients)


@app.get('/ingredients', response_model=List[str])
def get_all_ingredients():
    return get_ingredients()
