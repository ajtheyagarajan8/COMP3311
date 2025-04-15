#! /usr/bin/env python3


"""
COMP3311
25T1
Assignment 2
Pokemon Database

Written by: Arjun Theyagarajan z5477862
Written on: 24/04/2025

File Name: Q3
"""


import sys
import psycopg2
import helpers


### Constants
USAGE = f"Usage: {sys.argv[0]} <pokemon_name>"

query='''
SELECT
    m.name AS move_name,
    COUNT(DISTINCT l.learnt_in) AS num_games,
    ROUND(AVG(CAST(SUBSTRING(r.Assertion FROM 'Level: ([0-9]+)') AS INTEGER))) AS avg_level
FROM
    Learnable_Moves l
    JOIN Pokemon p ON p.id = l.Learnt_By
    JOIN Requirements r ON r.id = l.Learnt_When
    JOIN Moves m ON m.id = l.LEARNS
WHERE
    p.name = %s
    AND r.Assertion LIKE 'Level: %'
GROUP BY
    m.name
HAVING
    COUNT(DISTINCT l.learnt_in) >= 30
ORDER BY
    m.name ;'''

def main(db):
    ### Command-line args

    print(sys.argv[1])
    if len(sys.argv) != 2:
        print(USAGE)
        return 1

    pokemon_name = sys.argv[1]

    try:
        with db.cursor() as cur:
            cur.execute(query, [pokemon_name])
            results = cur.fetchall()

            helpers.pretty_print_cols(("MoveName", 16), ("#Games", 6), ("AvgLearntLevel", 16))

            for move_name, game, avg_learnt_level in results:
                helpers.pretty_print_cols((f"{type}", 16), (f"{game}", 6), (f"{avg_learnt_level}", 8))

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
