#!/usr/bin/env python3
import json
import random
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data' / 'name_pools'

FULL_NAMES = [
    "Mia Palmer", "Jenna Nighswonger", "Sam Meza", "Croix Bethune", "Lauren DeBeau",
    "Ally Schlegel", "Maya Doms", "Alexa Spaanstra", "Samar Guidry", "Valeska Silva",
    "Caterina Regazzoni", "Daniela Flores", "Annika Wohner", "Carolina Ferreira",
    "Andersen Williams", "Mayu Sasaki", "Michelle Cooper", "Raegan Kelley", "Grace Fisk",
    "Lauren Martinho", "Simone Jackson", "Brecken Mozingo", "Jameese Joseph",
    "Yazmeen Ryan", "Riley Tiernan", "Yuna McCormack", "Andrea Garcia", "Taylor Huff",
    "Kelsey Turnbow", "Kiara Gilday", "Haley Woodward", "Jaedyn Shaw", "Messiah Bright",
    "Hallie Mace", "Bryce Clements", "Paige Wheeler", "Ryan Campbell", "Amirah Ali",
    "Emina Ekic", "Lia Godfrey", "Hope Gaines", "Talia DellaPeruta", "Kelley Yearick",
    "Leah Klenke", "Lauren Berman", "Olivia Moultrie", "Mia Fishel", "Sydney Skipper",
    "Zoe Burns", "Madison Mercado", "Trinity Byars", "Savy King", "Beata Olsson",
    "Maisie Kufeld", "Bri Folds", "Quincy McMahon", "Maria Bolden", "Brianna Pinto",
    "Viviana Villacorta", "Ally Sentnor", "Amanda Dennis", "Drew Gustaitis",
    "Korbin Albert", "Jordan Canniff", "Taryn Torres", "Elaine Rouse", "Mayce Yarbrough",
    "Quinn McNeill", "Taylor Lemay", "Mimi Asom", "Gabby Provenzano", "Izzy D'Aquila",
    "Reilyn Turner", "Leah Loukas", "Samantha Kroeger", "Sophia Jones", "Ally Lemos",
    "Jordan Silkowitz", "Jill Flammia", "Ayo Oke", "Mary Long", "Chloe Ricketts",
    "Ellie Molli", "Nadia Riso", "Aislynn Crowder", "Sophia Aragon", "Sam Hiatt",
    "Sadie Seibert", "Hannah Bebar", "Morgan Kruk", "Lily Yonas", "Maya Antoine",
    "Croix Soto", "Evie Vitali", "Gigi Speer", "Nicole Douglas", "Alexis Loera",
    "Avery Patterson", "Bridget Doyle", "Jane Hatter", "Jordan Hobbs", "Lauren Stamps",
    "Michele Fischer", "Sydney Jones", "Amelie Leoni", "Hannah Stambaugh", "Korra Kuehn",
    "Lily Reale", "Olivia Wingate", "Sarah Sievert", "Priscilla Perez",
    "Esther O'Brien", "Maggie Graham", "Ally Russell", "Emma Sears", "Lexi Hutton",
    "Yaelin Padilla", "Sarah Langley", "Brianna Lee", "Mia Feist", "Emma Zummo",
    "Mia Torres", "Grace Restovich", "Elise Evans", "Bianca Bustamante", "Kiley Gilday",
    "Riley Baker", "Carsyn Currier", "Grace Yochum", "Jada Talley", "Kessler Faulkner",
    "Lauren Richardson", "Nicole Payne", "Taylor Bubb", "Trinity Peters", "Abby Hall",
    "Claire McKeever", "Haley Hopkins", "Julia Grosso", "Kaylee Leong", "Kim Bergstrom",
    "Rose Chandler", "Shae Holmes", "Sophia White", "Ava Collins", "Hannah Betfort",
    "Magali Krier", "Quincy McMahon", "Ryan Quirk", "Sophia Harrison", "Victoria Haugen",
    "Angelina Anderson", "Annie McTighe", "Darya Kuznetsova", "Gianna Gentile",
    "Grace Burke", "Jillian Rodriguez", "Jordan Canales", "Julia Moore", "Katie Bellucci",
    "Keelan Terrell", "Kensley Long", "Laney Rouse", "Lauryn Rynne", "Maggie Pierce",
    "Mia Berkely", "Natalie Means", "Olivia Walker", "Sadie Pry", "Samantha Sullivan",
    "Sydney Collins", "Virginia Sinclair", "Adriana Cruz", "Alex Morgan", "Ally Watt",
    "Brianna Martinez", "Carmen Stinson", "Cassie Short", "Cienna Arriaga",
    "Clara Robbins", "Delaney Phelps", "Ella Stevens", "Emma Garcia", "Eva Gaetino",
    "Grace Wisnewski", "Hannah Craft", "Isabella Harrington", "Jaelin Howell",
    "Jamie Shepherd", "Jenna Bike", "Jordan Gomes", "Julia Lester", "Kate Wiesner",
    "Katja Snoeijs", "Kaylie Collins", "Kennedy Fuller", "Kyla Ferry",
    "Leilani Nesbeth", "Lily Woodham", "Macy Jessen", "Makena Morris", "Mallory Burd",
    "Marissa Arias", "Megan Rapinoe", "Mia Pace", "Morgan Weaver", "Natalia Staude",
    "Nicole Markovic", "Paige Metayer", "Rebecca Watkins", "Reyna Reyes", "Sam Staab",
    "Sophie Hirst", "Tegan McGrady", "Trinity Rodman", "Tyler Lussi",
    "Vanessa DiBernardo",
    "Tanner Ijams", "Sophie Dawe", "Jordan Nytes", "Azul Alvarez", "Sara Wojdelko",
    "Cara Martin", "Payton O'Malley", "Batoul Reda", "Maggie Conrad", "Drew Stover",
    "Madi Valenti", "Caroline Dysart", "Caroline Birkel", "Jasmine Kessler",
    "Faith Nguyen", "Peyton Hull", "Victoria Safradin", "Leah Wolf", "Nyamma Nelson",
    "Genesis Perez Watson", "Noelle Henning", "Sierra McCluer", "Molly Pritchard",
    "Reagan Sulaver", "Erynn Floyd", "Karalyn Dail", "Izzy Lee", "Katie Bisgrove",
    "Ava de Leest", "Dani Eden", "Elizabeth Navola", "Leanne Trudel", "Mackenzie Gress",
    "Kailey Carlen", "Paula Flores", "Brianna Frey", "Riley Liebsack", "Leah Shaffer",
    "Caroline Ritter", "Maria Galley", "Hannah Folliard", "Valentina Amaral",
    "Jona Hennings", "Kyran Thievon", "Mallorie Benhart", "Sonoma Kasica",
    "Jillian Medvecky", "Isaac Ranson", "Cate Burns", "Mia Pongratz",
    "JuJu Watkins", "Hannah Hidalgo", "Paige Bueckers", "Teonni Key", "Aaliyah Nye",
    "Sa'Myah Smith", "Stailee Heard", "Syla Swords", "Te-Hina Paopao",
    "Mikaylah Williams", "Jordan Lee", "Emily Saunders", "Khamil Pierre",
    "Maria Conde", "Jordan Sanders", "Sarah Strong", "Eniya Russell",
    "Georgia Amoore", "Dontavia Waggoner", "Milan Harris", "Addison Deal",
    "Janiah Barker", "Raegan Ernst", "Aneesah Morrow", "Arianna Williams",
    "Sonia Citron", "Camille Hobby", "Tajianna Roberts", "Jordan Areman",
    "Jah'niya Cook", "Sanaa Redmond", "Lacey Hinkle", "Kennedi Watkins",
    "Destiny Adams", "Hailey Van Lith", "Kenzie Dowell", "Hailey Atwood",
    "Quincey Turner", "Mekira Webster", "Aislynn Hayes", "TiJera Calhoun",
    "Amaya Oliver", "Reagan Willingham", "Zoe Brooks", "Gabby Casey",
    "Eleonora Villa", "Teresa Kiewiet", "Yahmani McKayle", "Ella Brubaker",
    "Meghan Andersen", "Amourie Porter", "Ra Shaya Kyle", "Talaysia Cooper",
    "Caia Elisaldez", "Izabella Zingaro", "Jalei Oglesby", "Ny'Ceara Pryor",
    "Bailey Maupin", "Raegan Beers", "Cassie Gallagher", "Jada Wynn",
    "Ryann Bennett", "Angelina Robles", "Ella Gallatin", "Kenley McCarn",
    "Alayna Kraus", "Alexis Bordas", "Bree Salenbien", "Lex Therien",
    "Avery Mills", "Erin Condron", "Kaylee Borden", "Gabby Mundy", "Kara Dunn",
    "Mady Cartwright", "Ashleigh Connor", "Lauren Olsen", "Lulu Twidale",
    "Snudda Collins", "Solè Williams", "Karlee White", "Lexus Bargesser",
    "Destiny Garrett", "Lani White", "Tiani Ellison", "Kiki Rice",
    "Aaliyah Collins", "Tasia Jordan", "McKinna Brackens", "Laycee Drake",
    "Zennia Thomas", "Hannah Riddick", "Aleshia Jones", "Shannon Dowell",
    "Meg Cahalan", "Fortuna Ngnawo", "Sierra Chambers", "Colbi Maples",
    "Nia Green", "Brianna Davis", "Charlise Dunn", "Rachel Ullstrom",
    "Jada Williams", "Skylar Forbes", "Bella Pucci", "Grace VanSlooten",
    "Zahra King", "Rori Cox", "Nene Ndiaye", "Julia Coleman", "Zoe Borter",
    "Nunu Agara", "Sabou Gueye", "Jakayla Johnson", "Priscilla Williams",
    "Jade Tillman", "India Johnston", "Meadow Roland", "Jenna Villa",
    "Maya Hernandez", "Aryss Macktoon", "Abbie Aalsma", "Zamareya Jones",
    "Peyton Hill", "Ta'Niya Latson", "Clare Coyle", "Crystal Schultz",
    "Tessa Towers", "Olivia Kulyk", "Mariyah Noel", "Edyn Battle",
    "Da'Brya Clark", "Caliyah DeVillasee", "Uche Izoje", "Anna Trusty",
    "Kate Dike", "Jess Lawson", "Jenna Guyer", "Nayo Lear", "Amanda Barcello",
    "Makenzie Luehring", "Tatum Thompson", "Paige Kohler",
    "Ashley Bible", "Reagan Ennist", "Lauren Medeck", "Julia Rienks",
    "Sophie Dufour", "Sydney Dunning", "Kylee Owens", "Mackenzie McGuire",
    "Élodie Lalonde", "Kali Jurgensmeier", "Claire Little", "Aniya Clinton",
    "Jocelyn Jourdan", "Chloe Monson", "Kyra McKelvey", "Alaleh Tolliver",
    "TaKenya Stafford", "Victoria Barrett", "Lily Dykstra", "Olivia Hart",
    "Emerson Matthews", "Jillian Tippmann", "Logan King", "Jadyn Livings",
    "Elena Garcia-Guerrios", "Ally Cordes", "Ava Poinsett", "Jessica Ricks",
    "Cailin Demps", "Jalynn Brown", "Ella Vogel", "Taylor de Boer",
    "Kierstyn Barton", "Kendall Barnes", "Chloe Murakami", "Mara Stiglic",
    "Candela Alonso-Corcelles", "Delaney Russell", "Audrey Ross",
    "Brooke Gilleland", "Julia Leonardo", "Kira Holland", "Summer Kohler",
    "Haylee Brown", "Harper Murray", "Ashby Willis", "Kiera Hamilton",
    "Ksenia Rakhmanchik", "Jaida Harris", "Loryn Helgesen",
    "Kate Tyack", "Grace Walter", "Kayleigh Bender", "Shea Berigan",
    "Hanna Bodner", "Jane Fox", "Emma Ing", "Grace Murphy", "Amelia Pirozzi",
    "Dani Serrano", "Nikki Seven", "Anna Simmons", "Mim Suares-Jury",
    "Quinn Whitaker", "Ellie Bergin", "Maeve Brennan", "Mady Cheney",
    "Julia Givens", "Olivia Johnson", "Lily Toole", "Lexi Culp",
    "Sabrina Martin", "Natalie Shurtleff", "Katie Barr", "Callie Batchelder",
    "Ella Berg", "Ella Brunette", "Grace DeSimone", "Keira Doyle-Odenbach",
    "Madeline Egan", "Nancy Halleron", "Charlotte Hodgson", "Olivia Kelley",
    "Julia Kerr", "Ashley Kiernan", "Ava Kraszewski", "Anne Madden",
    "Megan Marco", "Brianna Mennella", "Kassidy Morris", "Lauren Picardi",
    "Shannon Smith", "Jamie Tanner", "Emma Toner", "Elizabeth Wamp",
    "Christina Warren", "Paige Willard", "Michelle Zhai", "Chloe Bowers",
    "Regan Byrne",
]

REGIONS = [
    "american_northeast", "american_south", "american_midwest",
    "american_west", "american_texas_southwest",
]

random.seed(42)

def extract_first_last(full_name):
    parts = full_name.strip().split()
    if len(parts) < 2:
        return None, None
    first = parts[0]
    last = parts[-1]
    first = first.strip("'")
    if len(first) <= 1 or len(last) <= 1:
        return None, None
    return first, last

def main():
    first_path = DATA_DIR / 'first_names.json'
    surname_path = DATA_DIR / 'surnames.json'

    with open(first_path) as f:
        first_data = json.load(f)
    with open(surname_path) as f:
        surname_data = json.load(f)

    existing_first_all = set()
    for region in REGIONS:
        existing_first_all.update(first_data.get(region, []))

    existing_surnames = set(surname_data.get("american_general", []))

    new_firsts = set()
    new_surnames = set()
    all_firsts = set()
    all_surnames = set()

    for name in FULL_NAMES:
        first, last = extract_first_last(name)
        if not first or not last:
            continue
        all_firsts.add(first)
        all_surnames.add(last)
        if first not in existing_first_all:
            new_firsts.add(first)
        if last not in existing_surnames:
            new_surnames.add(last)

    new_firsts_sorted = sorted(new_firsts)
    random.shuffle(new_firsts_sorted)

    for name in new_firsts_sorted:
        num_regions = random.randint(2, 4)
        chosen = random.sample(REGIONS, num_regions)
        for region in chosen:
            if name not in first_data.get(region, []):
                first_data.setdefault(region, []).append(name)

    for region in REGIONS:
        first_data[region] = sorted(set(first_data[region]))

    new_surnames_sorted = sorted(new_surnames)
    current_general = surname_data.get("american_general", [])
    current_general.extend(new_surnames_sorted)
    surname_data["american_general"] = sorted(set(current_general))

    with open(first_path, 'w') as f:
        json.dump(first_data, f, indent=2, ensure_ascii=False)
    with open(surname_path, 'w') as f:
        json.dump(surname_data, f, indent=2, ensure_ascii=False)

    print(f"=== NCAA Women's Name Processing Complete ===")
    print(f"Total full names processed: {len(FULL_NAMES)}")
    print(f"Unique first names extracted: {len(all_firsts)}")
    print(f"Unique surnames extracted: {len(all_surnames)}")
    print(f"NEW first names added: {len(new_firsts)}")
    print(f"NEW surnames added: {len(new_surnames)}")
    print()
    print("First names added per region:")
    for region in REGIONS:
        count = len([n for n in new_firsts if n in first_data.get(region, [])])
        print(f"  {region}: {count} new names (total: {len(first_data[region])})")
    print(f"\nSurnames in american_general: {len(surname_data['american_general'])} total")
    print(f"\nNew first names: {sorted(new_firsts)[:20]}{'...' if len(new_firsts) > 20 else ''}")
    print(f"New surnames: {sorted(new_surnames)[:20]}{'...' if len(new_surnames) > 20 else ''}")

if __name__ == "__main__":
    main()
