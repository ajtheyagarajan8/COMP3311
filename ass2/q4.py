#! /usr/bin/env python3
"""
COMP3311
25T1
Assignment 2
Pokemon Database

Written by: <YOUR NAME HERE> <YOUR STUDENT ID HERE>
Written on: <DATE HERE>

File Name: Q4
"""


import sys
import psycopg2
import helpers
from collections import defaultdict


### Constants
USAGE = f"Usage: {sys.argv[0]} <pokemon_name>"

query1 = '''
WITH RECURSIVE EvolutionChain AS (
    -- Base case: start with Pokémon matching name
    SELECT
        pre.ID AS Start_ID,
        pre.Name AS Start_Name,
        post.ID AS Next_ID,
        post.Name AS Next_Name,
        e.ID AS Evolution_ID
    FROM Pokemon pre
    JOIN Evolutions e ON e.Pre_Evolution = pre.ID
    JOIN Pokemon post ON e.Post_Evolution = post.ID
    WHERE pre.Name ILIKE '%pik%' OR post.Name ILIKE '%pik%'

    UNION

    -- Recursive step: find further evolutions of already discovered evolutions
    SELECT
        ec.Start_ID,
        ec.Start_Name,
        post.ID AS Next_ID,
        post.Name AS Next_Name,
        e.ID AS Evolution_ID
    FROM EvolutionChain ec
    JOIN Evolutions e ON e.Pre_Evolution = ec.Next_ID
    JOIN Pokemon post ON e.Post_Evolution = post.ID
)

SELECT
    ec.Start_Name AS From_Pokemon,
    ec.Next_Name AS To_Pokemon,
    r.Assertion AS Requirement,
    er.Inverted
FROM EvolutionChain ec
LEFT JOIN Evolution_Requirements er ON er.Evolution = ec.Evolution_ID
LEFT JOIN Requirements r ON er.Requirement = r.ID
ORDER BY ec.Start_Name, ec.Next_Name, r.Assertion;
'''

query = '''
WITH RECURSIVE EvolutionChain AS (
    -- Base case: start with all Pokémon with 'Pik' in their name
    SELECT
        pre.ID AS Start_ID,
        pre.Name AS Start_Name,
        post.ID AS Next_ID,
        post.Name AS Next_Name,
        e.ID AS Evolution_ID
    FROM Pokemon pre
    LEFT JOIN Evolutions e ON e.Pre_Evolution = pre.ID
    LEFT JOIN Pokemon post ON e.Post_Evolution = post.ID
    WHERE pre.Name ILIKE %s OR post.Name ILIKE %s

    UNION

    -- Recursive case: follow the evolution chain
    SELECT
        ec.Start_ID,
        ec.Start_Name,
        post.ID AS Next_ID,
        post.Name AS Next_Name,
        e.ID AS Evolution_ID
    FROM EvolutionChain ec
    JOIN Evolutions e ON e.Pre_Evolution = ec.Next_ID
    JOIN Pokemon post ON e.Post_Evolution = post.ID
)
SELECT
    ec.Start_Name AS From_Pokemon,
    ec.Next_Name AS To_Pokemon,
    r.Assertion AS Requirement,
    er.Inverted
FROM EvolutionChain ec
LEFT JOIN Evolution_Requirements er ON er.Evolution = ec.Evolution_ID
LEFT JOIN Requirements r ON er.Requirement = r.ID
ORDER BY r.id, ec.start_name, ec.next_name, r.assertion, er.inverted;
'''

def print_output(data):
    from collections import defaultdict

    evo_graph = defaultdict(list)
    reverse_graph = defaultdict(list)
    all_pokemon = set()

    for pre, post, req, inv in data:
        all_pokemon.add(pre)
        if post:
            all_pokemon.add(post)
            label = f"Not {req}" if inv else req
            evo_graph[pre].append((post, label))
            reverse_graph[post].append(pre)

    # Step 2: Find roots (no pre-evolutions)
    roots = [p for p in all_pokemon if not reverse_graph[p]]

    # Step 3: DFS to find all evolution chains
    def dfs(chain, current, chains, seen_paths):
        if current not in evo_graph:
            chain_key = tuple(p for p, _ in chain)
            if chain_key not in seen_paths:
                seen_paths.add(chain_key)
                chains.append(chain)
            return

        targets = defaultdict(list)
        for post, req in evo_graph[current]:
            targets[post].append(req)
        for post, reqs in targets.items():
            dfs(chain + [(post, reqs)], post, chains, seen_paths)

    full_chains = {}
    for root in roots:
        chains = []
        seen_paths = set()
        dfs([(root, [])], root, chains, seen_paths)
        full_chains[root] = chains

    # Step 4: Filter by search term
    query = sys.argv[1].lower()
    matching = [p for p in all_pokemon if query in p.lower()]
    
    # Step 5: Print results
    for name in sorted(matching):
        print(f"{name}: The full evolution chain:")

        # Special case: Pokémon with no evolutions or pre-evolutions
        if name not in evo_graph and not reverse_graph[name]:
            print(name)
            print("- No Evolutions")
            continue

        # Find root
        root = name
        while reverse_graph[root]:
            root = reverse_graph[root][0]

        chains = full_chains.get(root, [])
        printed = False
        list_main_names_printed = []

        # Filter the chains to only those involving the current name
        relevant_chains = [chain for chain in chains if any(name == p for p, _ in chain)]

        if relevant_chains:
            # Print the root only once
            print(relevant_chains[0][0][0])
            list_main_names_printed.append(relevant_chains[0][0][0])
            printed = True

            printed_steps = set()  # Track what's been printed at each depth

            for chain in relevant_chains:
                for depth, (post, reqs) in enumerate(chain[1:], start=1):
                    sorted_reqs = tuple(sorted(reqs, key=lambda r: (0 if "Region" in r else 1 if "Use Item" in r else 2, r)))
                    step_key = (post, sorted_reqs)
                    if step_key in printed_steps:
                        continue  # Skip duplicate step
                    printed_steps.add(step_key)

                    indent = '+' * depth
                    print(f"{indent} For \"{post}\", The evolution requirement is [{'] AND ['.join(sorted_reqs)}]")
        else:
            print(name)
            print("- No Evolutions")

def main(db):
    ### Command-line args
    if len(sys.argv) != 2:
        print(USAGE)
        return 1

    pokemon_name = sys.argv[1]

    try:
        with db.cursor() as cur:
            cur.execute(query,[f"%{pokemon_name}%",f"%{pokemon_name}%"] )
            rows = cur.fetchall()
            data = []
            for row in rows:
                from_pokemon, to_pokemon, requirement, inverted = row
                # Convert 't'/'f' to True/False
                if inverted in ('t', 'f'):  # From PostgreSQL boolean
                    inverted = inverted == 't'
                data.append((from_pokemon, to_pokemon, requirement, inverted))
            
            print_output(data)
    except psycopg2.Error as e:
        print("Query execution error:", e)
        return 1

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
