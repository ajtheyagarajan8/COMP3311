#! /usr/bin/env python3


"""
COMP3311
25T1
Assignment 2
Pokemon Database

Written by: <YOUR NAME HERE> <YOUR STUDENT ID HERE>
Written on: <DATE HERE>

File Name: Q2.py
"""


import sys
import psycopg2
import helpers


### Constants
USAGE = f"Usage: {sys.argv[0]}"

query='''
SELECT
    t.name,
    COUNT(DISTINCT m.id) AS num_moves,
    COUNT(DISTINCT p.id) AS num_pokemon_with_10_plus_moves
FROM types t
JOIN moves m ON m.of_type = t.id
-- count all moves of the type above

-- join to find pokemon who have learnt these moves
JOIN learnable_moves lm ON lm.learns = m.id
JOIN pokemon p ON p.id = lm.learnt_by AND p.first_type = t.id
JOIN PokemonWith10PlusSameTypeMoves ps ON ps.PokemonID = p.id
GROUP BY t.name;

'''

def main(db):
    ### Command-line args
    if len(sys.argv) != 1:
        print(USAGE)
        return 1

    try:
        with db.cursor() as cur:
            cur.execute(query)
            results = cur.fetchall()

            helpers.pretty_print_cols(("TypeName", 12), ("#Moves", 8), ("#Pokemon", 8))

            # Print each row
            for type, move_count, pokemon_count in results:
                helpers.pretty_print_cols((f"{type}", 12), (f"{move_count}", 8), (f"{pokemon_count}", 8))

    except psycopg2.Error as e:
            print("Query execution error:", e)
            return 1
        
    return 0


if __name__ == '__main__':
    exit_code = 0
    db = None
    try:
        db = psycopg2.connect(dbname="pkmon")
        exit_code = main(db)
    except psycopg2.Error as err:
        print("DB error: ", err)
        exit_code = 1
    except Exception as err:
        print("Internal Error: ", err)
        raise err
    finally:
        if db is not None:
            db.close()
    sys.exit(exit_code)

