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
    WHERE pre.Name ILIKE %s OR post.Name ILIKE %s

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
        cur.execute(query, [f"%{name}%", f"%{name}%"])
        rows = cur.fetchall()

        # Build evolution chains
        chains = {}
        involved = set()

        for pre, post, depth, name_chain, req, inv, evo_id in rows:
            if pre not in chains:
                chains[pre] = {}
            if post not in chains[pre]:
                chains[pre][post] = []
            chains[pre][post].append((req, inv))

            # Track base names for filtering
            involved.add(name_chain[0])

        # Get Pokémon with no evolutions that match the filter
        cur.execute('''
            SELECT Name
            FROM Pokemon
            WHERE Name ILIKE %s
              AND ID NOT IN (SELECT Pre_Evolution FROM Evolutions WHERE Pre_Evolution IS NOT NULL)
              AND ID NOT IN (SELECT Post_Evolution FROM Evolutions WHERE Post_Evolution IS NOT NULL)
        ''', [f"%{name}%"])
        no_evos = [row[0] for row in cur.fetchall()]

        # Combine both evolution bases and no-evo matches, filter by input
        matched_names = set()
        for pname in list(chains.keys()) + no_evos:
            if name in pname.lower():
                matched_names.add(pname)

        for pname in sorted(matched_names):
            print(f"{pname}: The full evolution chain:")
            print(pname)

            def print_evos(curr, indent=1):
                if curr not in chains:
                    print("- No Evolutions")
                    return
                for next_evo in sorted(chains[curr].keys()):
                    reqs = format_req(chains[curr][next_evo])
                    req_str = f"[{' AND '.join(reqs)}]" if reqs else "[No Requirement]"
                    print(f"{'+' * indent} For \"{next_evo}\", The evolution requirement is {req_str}")
                    print_evos(next_evo, indent + 1)

            print_evos(pname)

    return 0

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
