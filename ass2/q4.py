#! /usr/bin/env python3

import sys
import psycopg2

USAGE = f"Usage: {sys.argv[0]} <pokemon_name>"

query = '''
WITH RECURSIVE evolution_chain AS (
    SELECT
        e.Pre_Evolution,
        pre.Name AS Pre_Name,
        e.Post_Evolution,
        post.Name AS Post_Name,
        1 AS depth,
        ARRAY[pre.Name, post.Name] AS name_chain,
        e.ID AS evolution_id
    FROM Evolutions e
    JOIN Pokemon pre ON e.Pre_Evolution = pre.ID
    JOIN Pokemon post ON e.Post_Evolution = post.ID

    UNION ALL

    SELECT
        e.Pre_Evolution,
        pre.Name AS Pre_Name,
        e.Post_Evolution,
        post.Name AS Post_Name,
        ec.depth + 1 AS depth,
        ec.name_chain || post.Name,
        e.ID AS evolution_id
    FROM evolution_chain ec
    JOIN Evolutions e ON e.Pre_Evolution = ec.Post_Evolution
    JOIN Pokemon pre ON e.Pre_Evolution = pre.ID
    JOIN Pokemon post ON e.Post_Evolution = post.ID
)
SELECT
    ec.Pre_Name,
    ec.Post_Name,
    ec.depth,
    ec.name_chain,
    r.Assertion AS requirement,
    er.Inverted,
    ec.evolution_id
FROM evolution_chain ec
LEFT JOIN Evolution_Requirements er ON er.Evolution = ec.evolution_id
LEFT JOIN Requirements r ON er.Requirement = r.ID
ORDER BY ec.name_chain, ec.evolution_id, r.ID;
'''

def format_req(reqs):
    result = []
    seen = set()
    for req, inverted in reqs:
        if req:
            entry = f"Not {req}" if inverted else req
            if entry not in seen:
                result.append(entry)
                seen.add(entry)
    return result

def main(db):
    if len(sys.argv) != 2:
        print(USAGE)
        return 1

    name = sys.argv[1].lower()

    with db.cursor() as cur:
        # Run recursive query
        cur.execute(query)
        rows = cur.fetchall()

        # Parse results into chains
        chains = {}
        root_to_chain = {}
        # In the loop where you're building the chains dictionary, ensure to track pre-evolutions as well
        
        for pre, post, depth, name_chain, req, inv, evo_id in rows:
            root = name_chain[0]
            if root not in chains:
                chains[root] = {}
            if pre not in chains:
                chains[pre] = {}  # Ensure pre-evolution is added to the chain
            if post not in chains[pre]:
                chains[pre][post] = []
            chains[pre][post].append((req, inv))
            root_to_chain[root] = name_chain

        # Find Pokémon with no evolutions at all that match
        cur.execute('''
            SELECT Name
            FROM Pokemon
            WHERE Name ILIKE %s
              AND ID NOT IN (SELECT Pre_Evolution FROM Evolutions WHERE Pre_Evolution IS NOT NULL)
              AND ID NOT IN (SELECT Post_Evolution FROM Evolutions WHERE Post_Evolution IS NOT NULL)
        ''', [f"%{name}%"])
        no_evos = [row[0] for row in cur.fetchall()]

                # Only include root if it or any of its descendants contains the search substring
        matched_roots = set()

        def subtree_contains(pokemon, visited=None):
            if visited is None:
                visited = set()
            if pokemon in visited:
                return False
            visited.add(pokemon)
            if name in pokemon.lower():
                return True
            for next_evo in chains.get(pokemon, {}):
                if subtree_contains(next_evo, visited):
                    return True
            return False

        for root in root_to_chain:
            if subtree_contains(root):
                matched_roots.add(root)


        printed = set()

        def print_evos(curr, indent=1):
            if curr not in chains:
                return
            for next_evo in sorted(chains[curr].keys()):
                reqs = format_req(chains[curr][next_evo])
                req_str = ' AND '.join(f"[{r}]" for r in reqs) if reqs else "[No Requirement]"
                print(f"{'+' * indent} For \"{next_evo}\", The evolution requirement is {req_str}")
                print_evos(next_evo, indent + 1)

        for pname in sorted(matched_roots.union(no_evos)):
            if pname in printed or name.lower() not in pname.lower():
                continue
            print(f"{pname}: The full evolution chain:")
            print(pname)
            if pname in chains:
                print_evos(pname)
            else:
                print("- No Evolutions")
            printed.add(pname)

if __name__ == '__main__':
    exit_code = 0
    db = None
    try:
        db = psycopg2.connect(dbname="pkmon")
        exit_code = main(db)
    except psycopg2.Error as err:
        print("DB error:", err)
        exit_code = 1
    except Exception as err:
        print("Internal Error:", err)
        raise
    finally:
        if db is not None:
            db.close()
    sys.exit(exit_code)
