from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from copy import deepcopy
from pydantic import BaseModel, Field, PrivateAttr, validator
from jsondb import ObjectStorage, PrimitiveStorage
import re

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
    def missing_ingredients(self):
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


def filter_recipes_by_name(recipes, name):
    recipes_matching_name = []
    requested_name = r"(\s|^)" + name.lower()
    for recipe in recipes:
        recipe_contains_searched_word = re.search(requested_name, recipe.name, re.IGNORECASE)
        if recipe_contains_searched_word:
            recipes_matching_name.append(deepcopy(recipe))
    return recipes_matching_name


def sort_recipes_by_ingredients(recipes, ingredients):
    ingredient_set = set([i.lower() for i in ingredients])
    local_recipes = deepcopy(recipes)
    for r in local_recipes:
        r.compare_ingredients(ingredient_set)
    return sorted(local_recipes, key=lambda r: r.missing_ingredients)

def get_ingredients():
    ingredients = PrimitiveStorage('ingredients').read()
    return [i.lower() for i in ingredients]


def save_ingredients(new_entries):
    PrimitiveStorage('ingredients').create(new_entries)


@app.get('/recipes', response_model=List[RecipeModel])
def get_a_page_of_recipes():
    return get_recipes()


@app.get('/recipes/search', response_model=List[RecipeModel])
def search_recipes(ingredients: List[str] = Query([]), name: str = ''):
    recipes_matching_name = filter_recipes_by_name(get_recipes(), name)
    return sort_recipes_by_ingredients(recipes_matching_name, ingredients)


@app.post('/recipes')
def add_new_recipe(recipe: RecipeModel):
    save_recipe(recipe.dict())
    save_ingredients(recipe.ingredients)


@app.get('/ingredients', response_model=List[str])
def get_all_ingredients():
    return get_ingredients()
