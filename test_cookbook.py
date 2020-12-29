import os

import pytest
from fastapi.testclient import TestClient
from unittest import mock
from cookbook import app, RecipeModel
from conftest import Stub

client = TestClient(app)

HTTP_SUCCESS = 200


def fake_db_with_read(data):
    mock_db = mock.Mock()
    mock_db.read = mock.Mock(return_value=data)
    return mock_db


@pytest.fixture()
def valid_fake_recipe():
    return {
        'name': 'Hello',
        'url': 'hello',
        'ingredients': ['a', 'b', 'c'],
        'tags': ['x', 'y', 'z'],
    }


class TestRecipeModel:
    def test_can_validate_good_data(self, valid_fake_recipe):
        assert RecipeModel(**valid_fake_recipe)

    def test_raises_exception_when_name_is_shorter_than_5(self, valid_fake_recipe):
        bad_fake_recipe = {
            **valid_fake_recipe,
            'name': '1234',
        }
        good_fake_recipe = {
            **valid_fake_recipe,
            'name': '12345',
        }
        assert RecipeModel(**good_fake_recipe)
        with pytest.raises(Exception) as e:
            recipe = RecipeModel(**bad_fake_recipe)
        assert e.value.errors()[0]['loc'][0] == 'name'

    def test_raises_exception_when_url_is_shorter_than_5(self, valid_fake_recipe):
        bad_fake_recipe = {
            **valid_fake_recipe,
            'url': '1234',
        }
        good_fake_recipe = {
            **valid_fake_recipe,
            'url': '12345',
        }
        assert RecipeModel(**good_fake_recipe)
        with pytest.raises(Exception) as e:
            recipe = RecipeModel(**bad_fake_recipe)
        assert e.value.errors()[0]['loc'][0] == 'url'

    def test_converts_ingredients_to_lowercase(self, valid_fake_recipe):
        input_ingredients = ['AaaA', 'BBbb', 'ccc', 'DD']
        expected_ingredients = ['aaaa', 'bbbb', 'ccc', 'dd']
        fake_recipe = {
            **valid_fake_recipe,
            'ingredients': input_ingredients,
        }
        recipe = RecipeModel(**fake_recipe)
        assert recipe.ingredients == expected_ingredients

    def test_converts_tags_to_lowercase(self, valid_fake_recipe):
        input_tags = ['AaaA', 'BBbb', 'ccc', 'DD']
        expected_tags = ['aaaa', 'bbbb', 'ccc', 'dd']
        fake_recipe = {
            **valid_fake_recipe,
            'tags': input_tags,
        }
        recipe = RecipeModel(**fake_recipe)
        assert recipe.tags == expected_tags

    def test_strips_whitespace_from_all_strings(self):
        good_recipe = {
            'name': ' aaaaaaa ',
            'url': ' bbbbbbb ',
            'ingredients': [' x ', ' y '],
            'tags': [' i ', ' j '],
        }
        recipe = RecipeModel(**good_recipe)
        assert recipe.name == good_recipe['name'].strip()
        assert recipe.url == good_recipe['url'].strip()
        assert recipe.ingredients == [i.strip() for i in good_recipe['ingredients']]
        assert recipe.tags == [t.strip() for t in good_recipe['tags']]


class TestRecipeRoutes:
    @mock.patch('cookbook.ObjectStorage')
    def test_can_fetch_recipes(self, db_stub):
        expected_recipes = [
            {'url': 'abcdef', 'name': 'French Toast', 'ingredients': ['a', 'b'], 'tags': ['c', 'd']},
            {'url': 'abcdef', 'name': 'English Muffin', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': 'Montreal Bagel', 'ingredients': [], 'tags': []},
        ]
        db_stub.return_value = fake_db_with_read(expected_recipes)
        response = client.get('/recipes')

        assert response.status_code == HTTP_SUCCESS
        assert response.json() == expected_recipes
        assert Stub(db_stub).called_with('recipes')


    @mock.patch('cookbook.ObjectStorage')
    def test_limit_number_of_returned_recipes(self, db_stub):
        expected_recipes = [
            {'url': 'abcdef', 'name': '111111', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '222222', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '333333', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '444444', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '555555', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '666666', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '777777', 'ingredients': [], 'tags': []},
        ]
        db_stub.return_value = fake_db_with_read(expected_recipes)
        max_recipes = 5
        with mock.patch.dict(os.environ, {'COOKBOOK_PAGE_LIMIT': str(max_recipes)}):
            response = client.get('/recipes')

        assert response.json() == expected_recipes[:max_recipes]

    @mock.patch('cookbook.PrimitiveStorage')
    def test_can_fetch_all_ingredients_in_lower_case(self, db_stub):
        expected_ingredients = ['D', 'Aaa', 'BBBB', 'ccC', 'ddddd']
        db_stub.return_value = fake_db_with_read(expected_ingredients)
        response = client.get('/ingredients')

        assert response.status_code == HTTP_SUCCESS
        assert response.json() == [i.lower() for i in expected_ingredients]
        assert Stub(db_stub).called_with('ingredients')

    @mock.patch('cookbook.ObjectStorage')
    @mock.patch('cookbook.PrimitiveStorage', new=mock.Mock())
    def test_can_add_new_recipe(self, db_stub, valid_fake_recipe):
        response = client.post('/recipes', json=valid_fake_recipe)

        assert response.status_code == HTTP_SUCCESS
        assert Stub(db_stub).has_call_with('recipes')
        assert Stub(db_stub().create).has_call_with(valid_fake_recipe)

    @mock.patch('cookbook.ObjectStorage', new=mock.Mock())
    @mock.patch('cookbook.PrimitiveStorage')
    def test_a_new_recipe_also_adds_ingredients(self, db_stub, valid_fake_recipe):
        new_ingredients = ['eggs', 'cheese', 'oil', 'salt']
        new_recipe = {
            **valid_fake_recipe,
            'ingredients': new_ingredients,
        }
        db_stub.return_value = fake_db_with_read([])
        response = client.post('/recipes', json=new_recipe)

        assert Stub(db_stub).has_call_with('ingredients')
        assert Stub(db_stub().create).has_call_with(new_ingredients)

    @mock.patch('cookbook.ObjectStorage')
    def test_get_recipes_in_order_of_least_mismatching_ingredients_ignoring_query_case(self, db_stub):
        all_recipes = [
            {'url': 'abcdefg', 'name': 'Garlic Bread', 'ingredients': ['bread', 'garlic'], 'tags': []},
            {'url': 'abcdefg', 'name': 'Omelet', 'ingredients': ['eggs', 'onion', 'salt', 'pepper'], 'tags': []},
            {'url': 'abcdefg', 'name': 'Turkey Roast', 'ingredients': ['turkey', 'onion', 'salt'], 'tags': []},
            {'url': 'abcdefg', 'name': 'Hash Browns', 'ingredients': ['eggs', 'potato', 'flour', 'salt'], 'tags': []},
            {'url': 'abcdefg', 'name': 'Cookies', 'ingredients': ['eggs', 'flour', 'sugar'], 'tags': []},
        ]
        expected_order = [all_recipes[4], all_recipes[3], all_recipes[1], all_recipes[2], all_recipes[0]]
        db_stub.return_value = fake_db_with_read(all_recipes)
        response = client.get('/recipes/search', params={
            'ingredients': ['EGGS', 'SalT', 'fLOUr', 'sugar']
        })

        assert response.status_code == HTTP_SUCCESS
        assert response.json() == expected_order

    @mock.patch('cookbook.ObjectStorage')
    def test_search_recipes_by_word_in_title(self, db_stub):
        all_recipes = [
            {'url': 'abcdefg', 'name': 'Garlic Bread', 'ingredients': [], 'tags': []},
            {'url': 'abcdefg', 'name': 'Omelet', 'ingredients': [], 'tags': []},
            {'url': 'abcdefg', 'name': 'Turkey Roast', 'ingredients': [], 'tags': []},
            {'url': 'abcdefg', 'name': 'Roast Beef', 'ingredients': [], 'tags': []},
            {'url': 'abcdefg', 'name': 'Roasted Pineapple', 'ingredients': [], 'tags': []},
            {'url': 'abcdefg', 'name': 'Preroasted apples', 'ingredients': [], 'tags': []},
            {'url': 'abcdefg', 'name': 'Cookies', 'ingredients': [], 'tags': []},
        ]
        db_stub.return_value = fake_db_with_read(all_recipes)
        response = client.get('/recipes/search', params={'name': 'cookie'})
        assert response.json() == all_recipes[-1:]

        response = client.get('/recipes/search', params={'name': 'roast'})
        assert response.json() == all_recipes[2:5]

    @mock.patch('cookbook.ObjectStorage')
    def test_limit_number_of_returned_recipes_when_searching(self, db_stub):
        expected_recipes = [
            {'url': 'abcdef', 'name': '111111', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '222222', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '333333', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '444444', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '555555', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '666666', 'ingredients': [], 'tags': []},
            {'url': 'abcdef', 'name': '777777', 'ingredients': [], 'tags': []},
        ]
        db_stub.return_value = fake_db_with_read(expected_recipes)
        max_recipes = 5
        with mock.patch.dict(os.environ, {'COOKBOOK_PAGE_LIMIT': str(max_recipes)}):
            response = client.get('/recipes/search')

        assert response.json() == expected_recipes[:max_recipes]
