#! /usr/bin/env python3


"""
COMP3311
25T1
Assignment 2
Pokemon Database

Written by: Arjun Theyagarajan - z5477862
Written on: 22-04-2025

File Name: Q1.py
"""



import sys
import psycopg2
import helpers


### Constants
USAGE = f"Usage: {sys.argv[0]}"

def main(db):
    ### Command-line args
    if len(sys.argv) != 1:
        print(USAGE)
        return 1

    #query = "select * from pkmon where "
    studentQuery = '''
    SELECT g.Name AS Game,
       COUNT(DISTINCT pwg.Egg_group) AS Num_Distinct_Egg_Groups,
       COUNT(DISTINCT p.ID) AS Num_Distinct_Pokemon
FROM Games g
JOIN Pokedex pd ON g.ID = pd.Game
JOIN Pokemon p ON pd.National_ID = p.ID
LEFT JOIN PokemonWithEggGroups pwg ON p.ID = pwg.PokemonID
GROUP BY g.Name
ORDER BY g.Name;
'''
    
    try:
        with db.cursor() as cur:
            cur.execute(studentQuery)
            results = cur.fetchall()

            # Print header
            helpers.pretty_print_cols(("GameName", 17), ("#EggGroup", 9), ("Pokemon", 8))

            # Print each row
            for game, egg_groups, pokemons in results:
                helpers.pretty_print_cols((f"{game}", 17), (f"{egg_groups}", 9), (f"{pokemons}", 8))

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


