#!/usr/bin/env python3
"""
convert_questions_yesno.py — Dataset Converter for DeepThought Experiments
==========================================================================
Converts the MIX and PRO datasets from open-ended / multiple-choice question
format into TRUE/FALSE proposition format suitable for DeepThought's binary
voting system.

Usage:
    python3 convert_questions_yesno.py

Output:
    datasets/q_100_MIX_yesno.json
    datasets/q_60_PRO_yesno.json
"""

import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)

INPUT_MIX = os.path.join(PROJECT_DIR, "dataset-questions_translated", "q_100_MIX.json")
INPUT_PRO = os.path.join(PROJECT_DIR, "dataset-questions_translated", "q_60_PRO.json")

OUTPUT_DIR = os.path.join(SCRIPT_DIR, "datasets")
OUTPUT_MIX = os.path.join(OUTPUT_DIR, "q_100_MIX_yesno.json")
OUTPUT_PRO = os.path.join(OUTPUT_DIR, "q_60_PRO_yesno.json")

# =============================================================================
# MIX Dataset — 100 questions → 100 TRUE propositions
# =============================================================================
# Each question is converted to a factually correct assertion.
# Ground truth is always TRUE. Categories mirror the original dataset structure.

MIX_PROPOSITIONS = [
    # Q1-Q10: Personal / Conversational
    ("An AI assistant does not have a personal name in the traditional sense.", "personal"),
    ("An AI assistant does not have an age, as it is a software program.", "personal"),
    ("An AI assistant is a software program and does not have a physical place of origin.", "personal"),
    ("An AI assistant is designed to answer questions and assist users with various tasks.", "personal"),
    ("An AI assistant does not have hobbies, as it is a software program.", "personal"),
    ("An AI assistant does not eat food and therefore does not have a favorite food.", "personal"),
    ("Weather conditions vary depending on geographic location and time of year.", "personal"),
    ("The current day of the week depends on the date and time zone.", "personal"),
    ("The current time depends on the observer's time zone.", "personal"),
    ("Humor is a form of communication that uses incongruity or surprise to provoke laughter.", "personal"),

    # Q11-Q20: Science (basic)
    ("The blue whale is the largest animal in the world.", "science"),
    ("Adult humans typically have 32 teeth.", "science"),
    ("There are five oceans on Earth: the Pacific, Atlantic, Indian, Southern, and Arctic.", "science"),
    ("The skin is the largest organ in the human body.", "science"),
    ("The camel is known as the 'ship of the desert'.", "science"),
    ("Mount Everest is the highest mountain in the world.", "science"),
    ("Eggs are animal-based products.", "science"),
    ("The boiling point of water at standard atmospheric pressure is 100 degrees Celsius.", "science"),
    ("A common year has 365 days, while a leap year has 366 days.", "science"),
    ("Mars is known as the 'Red Planet'.", "science"),

    # Q21-Q30: Science (advanced)
    ("Light travels in straight lines at approximately 299,792 kilometers per second in a vacuum.", "science"),
    ("Gravity is the force that attracts objects with mass toward each other.", "science"),
    ("The ampere is the SI unit of electric current.", "science"),
    ("A cell is the basic structural and functional unit of all living organisms.", "science"),
    ("Most terrestrial animals breathe by inhaling oxygen from the air into their lungs.", "science"),
    ("A chemical element is a substance that cannot be broken down into simpler substances by chemical reactions.", "science"),
    ("Plants perform photosynthesis by using sunlight, water, and carbon dioxide to produce glucose and oxygen.", "science"),
    ("The sky appears blue because of Rayleigh scattering, which scatters shorter blue wavelengths of sunlight more than other colors.", "science"),
    ("Metabolism is the set of chemical reactions in living organisms that maintain life, including converting food into energy.", "science"),
    ("Sound travels through a medium such as air, water, or solids as mechanical vibrations in the form of waves.", "science"),

    # Q31-Q40: History
    ("The Great Wall was built in China.", "history"),
    ("George Washington was the first President of the United States.", "history"),
    ("World War II started in 1939.", "history"),
    ("The four great inventions of China are papermaking, printing, gunpowder, and the compass.", "history"),
    ("The Great Pyramid of Giza is the most famous structure in ancient Egypt.", "history"),
    ("Alexander Graham Bell is credited with inventing the telephone.", "history"),
    ("William Shakespeare was an English playwright and poet, widely regarded as one of the greatest writers in the English language.", "history"),
    ("The Renaissance originated in Italy, particularly in the city of Florence, during the 14th century.", "history"),
    ("Christopher Columbus is traditionally credited with the European discovery of the Americas in 1492.", "history"),
    ("Neil Armstrong was the first person to walk on the moon in 1969.", "history"),

    # Q41-Q50: Mathematics
    ("The sum of 1 and 1 is 2.", "mathematics"),
    ("The formula for the circumference of a circle is C = 2πr, where r is the radius.", "mathematics"),
    ("The sum of the interior angles of a triangle is 180 degrees.", "mathematics"),
    ("A prime number is a natural number greater than 1 that has no positive divisors other than 1 and itself.", "mathematics"),
    ("The product of 9 and 8 is 72.", "mathematics"),
    ("The Pythagorean theorem states that in a right triangle, the square of the hypotenuse equals the sum of the squares of the other two sides (a² + b² = c²).", "mathematics"),
    ("There are 60 minutes in one hour.", "mathematics"),
    ("The arithmetic average is calculated by dividing the sum of all values by the number of values.", "mathematics"),
    ("A fraction is a numerical quantity that represents a part of a whole, expressed as one number divided by another.", "mathematics"),
    ("A square has four sides of equal length.", "mathematics"),

    # Q51-Q60: Language
    ("'Hello' in Chinese (Mandarin) is '你好' (Nǐ hǎo).", "language"),
    ("'Thank you' in French is 'Merci'.", "language"),
    ("The English alphabet consists of 26 letters from A to Z.", "language"),
    ("In grammar, the subject is who or what the sentence is about, and the predicate describes what the subject does or is.", "language"),
    ("'Apple' in Spanish is 'Manzana'.", "language"),
    ("A verb is a word that expresses an action, occurrence, or state of being.", "language"),
    ("'Cat' in English refers to a small domesticated carnivorous mammal with soft fur and retractile claws.", "language"),
    ("Standard Mandarin Chinese has four main tones plus a neutral tone.", "language"),
    ("'Hello' in German is 'Hallo'.", "language"),
    ("'Goodbye' is a parting expression used when leaving someone or ending a conversation.", "language"),

    # Q61-Q70: Culture / Festivals
    ("Traditional Chinese festivals include the Spring Festival, Lantern Festival, Qingming Festival, Dragon Boat Festival, and Mid-Autumn Festival.", "culture"),
    ("The Chinese New Year (Spring Festival) is considered one of the largest and most widely celebrated festivals in the world.", "culture"),
    ("Christmas is a Christian holiday celebrated on December 25th that commemorates the birth of Jesus Christ.", "culture"),
    ("Spring Festival customs include family reunions, red decorations, fireworks, exchanging red envelopes, and eating traditional foods like dumplings.", "culture"),
    ("Halloween originates from the ancient Celtic festival of Samhain, marking the end of the harvest season and the beginning of winter.", "culture"),
    ("The Mid-Autumn Festival is a traditional Chinese festival celebrated on the 15th day of the 8th lunar month, associated with moon-watching and eating mooncakes.", "culture"),
    ("New Year's Day is celebrated on January 1st in the Gregorian calendar.", "culture"),
    ("Famous world cuisines include French, Italian, Chinese, Japanese, Indian, Mexican, and Thai cuisine.", "culture"),
    ("Hanfu is the traditional clothing of the Han Chinese people, characterized by flowing robes and cross-collar designs.", "culture"),
    ("Yoga is an ancient physical, mental, and spiritual practice originating from India that combines postures, breathing techniques, and meditation.", "culture"),

    # Q71-Q80: Geography
    ("The Nile River is traditionally considered the longest river in the world, at approximately 6,650 kilometers.", "geography"),
    ("There are seven continents on Earth: Africa, Antarctica, Asia, Australia, Europe, North America, and South America.", "geography"),
    ("The Pacific Ocean is located between Asia and Australia to the west and the Americas to the east.", "geography"),
    ("The Himalayas extend across five countries: Nepal, China (Tibet), India, Bhutan, and Pakistan.", "geography"),
    ("Africa is a continent, not a country, and therefore does not have a single capital city.", "geography"),
    ("The Earth's geographic North Pole is located in the middle of the Arctic Ocean.", "geography"),
    ("Russia is the country with the largest area in the world.", "geography"),
    ("Antarctica has no permanent residents, but it hosts rotating scientific research personnel at various research stations.", "geography"),
    ("China has 23 provinces, 5 autonomous regions, 4 municipalities, and 2 special administrative regions.", "geography"),
    ("The main languages in Europe include English, French, German, Spanish, Italian, Portuguese, Russian, and Dutch.", "geography"),

    # Q81-Q90: Entertainment
    ("Music genres are diverse and include classical, jazz, rock, pop, hip-hop, electronic, and many others.", "entertainment"),
    ("James Cameron directed the movie 'Avatar'.", "entertainment"),
    ("Hollywood is a neighborhood in Los Angeles, California, widely recognized as the historical center of the American film industry.", "entertainment"),
    ("Some of the most famous bands in the world include The Beatles, The Rolling Stones, Led Zeppelin, Queen, and Pink Floyd.", "entertainment"),
    ("Color preferences are subjective and vary among individuals based on personal experiences and cultural associations.", "entertainment"),
    ("Ballet is a highly technical form of dance that originated in the Italian Renaissance courts and was later developed in France and Russia.", "entertainment"),
    ("Karaoke is a form of interactive entertainment originating from Japan where people sing along to recorded music using a microphone.", "entertainment"),
    ("The Bible is the best-selling book of all time, with an estimated 5 billion copies sold.", "entertainment"),
    ("Video games are electronic games played on a computing device, involving interaction with a user interface to generate visual feedback.", "entertainment"),
    ("The most popular sports globally include association football (soccer), cricket, basketball, field hockey, and tennis.", "entertainment"),

    # Q91-Q100: Technology
    ("Artificial intelligence is a branch of computer science focused on creating systems capable of performing tasks that typically require human intelligence.", "technology"),
    ("Blockchain is a decentralized digital ledger technology that records transactions across multiple computers in a way that prevents retroactive alteration.", "technology"),
    ("ENIAC (Electronic Numerical Integrator and Computer) is generally considered the first general-purpose electronic digital computer.", "technology"),
    ("A smartphone is a handheld personal computer with a mobile operating system featuring advanced capabilities beyond basic telephony.", "technology"),
    ("The internet is a global network of interconnected computer networks that communicate using standardized protocols.", "technology"),
    ("Virtual reality is a computer-generated simulation of a three-dimensional environment that can be interacted with using specialized electronic equipment.", "technology"),
    ("Thomas Edison is credited with inventing the first commercially practical incandescent light bulb in 1879.", "technology"),
    ("Social media refers to interactive digital platforms that allow users to create, share, and exchange content in virtual communities and networks.", "technology"),
    ("5G is the fifth generation of mobile network technology, offering significantly faster data speeds, lower latency, and greater capacity than 4G.", "technology"),
    ("Programming is the process of creating a set of instructions that tell a computer how to perform a task, using programming languages.", "technology"),
]

# =============================================================================
# PRO Dataset — 60 questions → 60 TRUE propositions
# =============================================================================
# Each multiple-choice physics question is converted to an assertion about
# the correct answer. Format: compact assertion about the correct option.
# Education levels: junior_high (Q1-20), high_school (Q21-40), university (Q41-60)

PRO_PROPOSITIONS = [
    # Junior High School Physics (Q1-Q20)
    ("Regarding information transmission, the Beidou satellite positioning system can provide 24/7 instant positioning services (option A).", "junior_high"),
    ("The statement in line with actual situations is that the walking speed of an adult is about 1.1 m/s (option B).", "junior_high"),
    ("Regarding measuring instruments, mercury thermometers use the principle of liquid thermal expansion and contraction (option A).", "junior_high"),
    ("Regarding molecular dynamic theory, the incorrect statement is that molecules are the smallest particles that make up substances (option C).", "junior_high"),
    ("Regarding safe electricity use, the wrong practice is to cut off the pins that protect the ground wire in the three-pin plug (option B).", "junior_high"),
    ("Regarding temperature, heat, and internal energy, when the temperature of an object decreases, its internal energy will definitely decrease (option C).", "junior_high"),
    ("The correct statement is that crystals have fixed melting points (option D).", "junior_high"),
    ("Taking Xiao Ming as a reference, Xiao Hong's speed is 2 m/s when they walk in opposite directions (option A).", "junior_high"),
    ("Regarding internal energy, in diffusion phenomena molecules can move from low-temperature objects to high-temperature objects (option D).", "junior_high"),
    ("Regarding heat movement, the incorrect statement is that there is only repulsion between solids (option C).", "junior_high"),
    ("In Xiao Ming's physics notes, the wrong statement is that a moving pulley can change the direction of force (option B).", "junior_high"),
    ("Regarding temperature, internal energy, and heat, both work and heat transfer can change the internal energy of an object (option B).", "junior_high"),
    ("Regarding home circuits and safe electricity use, the refrigerator must use a three-hole socket (option C).", "junior_high"),
    ("The scenario that can reduce friction is a hovercraft sailing off the surface (option A).", "junior_high"),
    ("Regarding lenses, a projector is used to enlarge the picture (option A).", "junior_high"),
    ("Regarding the Hong Kong-Zhuhai-Macao Bridge undersea tunnel, it takes at least 34.2 minutes to pass through (option C).", "junior_high"),
    ("Regarding seasonal phenomena, in late autumn the white frost on grass leaves is a condensation (deposition) phenomenon (option B).", "junior_high"),
    ("At the Ertan Reservoir, water looking shallower than it actually is demonstrates the refraction of light (option C).", "junior_high"),
    ("Among energy sources, solar energy causes the least pollution to the environment (option D).", "junior_high"),
    ("Regarding mechanical energy, the incorrect statement is that as long as an object's position changes, its gravitational potential energy will definitely change (option C).", "junior_high"),

    # High School Physics (Q21-Q40)
    ("In the softball projectile motion problem, the time of a softball moving in the air is determined only by the height of the hit point from the ground (option D).", "high_school"),
    ("Among the ratiometric definitions, acceleration a = F/m is not defined using the ratiometric method (option C).", "high_school"),
    ("Regarding Brownian motion, it is the irregular motion of suspended particles (option B).", "high_school"),
    ("When a force opposite to velocity gradually decreases during uniform motion, acceleration increases, velocity increases, and displacement increases (option C).", "high_school"),
    ("In EC decay, the mass number of the nucleus remains unchanged while the atomic number is reduced by 1 (option A).", "high_school"),
    ("Regarding electric fields, the direction of the electric field intensity at a point is the same as the direction of the force on a positive charge at that point (option D).", "high_school"),
    ("Among the optical phenomena listed, chopsticks inserted obliquely in water appearing bent upward is a refraction phenomenon (option D).", "high_school"),
    ("When a horizontal tension is applied to a stationary object on a smooth surface, the object obtains acceleration immediately (option B).", "high_school"),
    ("In the double-slit interference experiment with 589 nm light, the spacing between the double slits is 1.68 × 10⁻⁴ m (option C).", "high_school"),
    ("Regarding artificial Earth satellites, the higher the orbit from the ground, the greater the mechanical energy but the smaller the operating speed (option B).", "high_school"),
    ("When a car is driving at rated power, it is impossible to perform uniformly accelerated linear motion (option B).", "high_school"),
    ("For an object sliding from a smooth incline with 30° angle and 2 m length, at the midpoint the mechanical energy is 0 J and kinetic energy is 5 J (option C).", "high_school"),
    ("Regarding the spring vibrator performing simple harmonic vibration with period T, if elastic force impulse is zero within time Δt, then Δt may be less than T/4 (option D).", "high_school"),
    ("In the International System of Units, the basic units are kg, m, and s (option D).", "high_school"),
    ("Regarding molecular physics, the small dewdrops on leaves are spherical due to liquid surface tension (option B).", "high_school"),
    ("Among the listed measures, installing lightning needles on top of tall buildings is to prevent harm caused by static electricity (option D).", "high_school"),
    ("Regarding a bicycle tire exposed to sun, the correct descriptions are ②③④ (option B).", "high_school"),
    ("Regarding overweight and weightlessness, astronauts in the International Space Station are in a weightless state (option D).", "high_school"),
    ("In the neutron-nucleus elastic collision, the ratio of neutron speed before to after collision is (A+1)/(A-1) (option A).", "high_school"),
    ("Regarding the Beidou satellite in circular orbit with radius r and period T, the average density of the Earth is ρ = 3πr³/(GT²R³) (option C).", "high_school"),

    # University Physics (Q41-Q60)
    ("When irradiated light wavelength changes from 400 nm to 300 nm, the stop voltage in the photoelectric effect increases by 1.035 V (option D).", "university"),
    ("When the sound source S is stationary and receiver R moves away, the vibration frequency of particle P at the midpoint is νs (option A).", "university"),
    ("Regarding photoelectric and Compton effects, the photoelectric effect absorbs photons while the Compton effect is equivalent to elastic collision of photons and electrons (option D).", "university"),
    ("Regarding photoelectric effect statements, the correct ones are (2) and (4) (option D).", "university"),
    ("Regarding simultaneity in special relativity, two events occurring at the same place and time in one inertial system occur simultaneously in all inertial systems (option A).", "university"),
    ("When a metal irradiated with monochromatic light of frequency 2ν, the maximum kinetic energy of the escaped photoelectron is hν + Ek (option D).", "university"),
    ("For the aircraft problem with 200 km/h airspeed, 56 km/h east wind, and 192 km/h ground speed, the direction is south or north (option C).", "university"),
    ("For helium and oxygen at the same temperature and pressure, the average translational kinetic energy w is equal but average kinetic energy ε is not equal (option C).", "university"),
    ("Regarding simultaneity, two events at the same location and time in one inertial system must occur simultaneously in another inertial system (option C).", "university"),
    ("For two Carnot heat engines with equal cycle curve areas, the difference between heat absorbed and heat released must be equal (option D).", "university"),
    ("For ideal gas undergoing adiabatic expansion, isochoric cooling, and isothermal compression, during the entire cycle the gas expels heat to the outside (option A).", "university"),
    ("For two metal spheres with radii R and r connected by wire, the charge surface density ratio σR/σr equals r/R (option D).", "university"),
    ("For identical containers with ammonia and hydrogen at equal pressure and temperature, to raise ammonia by the same temperature as 5 J raises hydrogen, 6 J of heat is needed (option A).", "university"),
    ("Regarding Gauss's theorem, if E on the Gaussian surface is not zero everywhere, there must be a charge inside the surface (option C).", "university"),
    ("For two concentric charged spheres, when Ra < r < Rb, the electric field intensity is Qa/(4πε₀r²) (option D).", "university"),
    ("Regarding reversible and irreversible processes, statements (1) and (4) are correct (option D).", "university"),
    ("Regarding electric displacement lines, they start from positive free charges and end at negative free charges, and do not intersect in charge-free space (option C).", "university"),
    ("Regarding Gauss's theorem, the D flux of the Gaussian surface is only related to the free charge in the plane (option C).", "university"),
    ("Among the given statements about thermodynamics, only statements (2) and (3) are correct (option C).", "university"),
    ("In the Newton's ring experiment with refractive index n medium, the dark ring radius expression is rk = √(kλR/n) (option B).", "university"),
]


def convert_mix(input_path: str, output_path: str) -> int:
    """Convert MIX dataset to yes/no propositions."""
    with open(input_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    if len(questions) != len(MIX_PROPOSITIONS):
        print(f"  ⚠️  Warning: MIX has {len(questions)} questions but {len(MIX_PROPOSITIONS)} propositions defined.")

    propositions = []
    for i, (q, (prop, cat)) in enumerate(zip(questions, MIX_PROPOSITIONS)):
        propositions.append({
            "id": i + 1,
            "original_question": q["question"],
            "proposition": prop,
            "ground_truth": True,
            "category": cat,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(propositions, f, indent=2, ensure_ascii=False)

    return len(propositions)


def convert_pro(input_path: str, output_path: str) -> int:
    """Convert PRO dataset to yes/no propositions."""
    with open(input_path, "r", encoding="utf-8") as f:
        questions = json.load(f)

    if len(questions) != len(PRO_PROPOSITIONS):
        print(f"  ⚠️  Warning: PRO has {len(questions)} questions but {len(PRO_PROPOSITIONS)} propositions defined.")

    propositions = []
    for i, (q, (prop, level)) in enumerate(zip(questions, PRO_PROPOSITIONS)):
        propositions.append({
            "id": i + 1,
            "original_question": q["question"],
            "proposition": prop,
            "ground_truth": True,
            "category": "physics",
            "education_level": level,
        })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(propositions, f, indent=2, ensure_ascii=False)

    return len(propositions)


def main():
    print("=" * 60)
    print("  DeepThought Dataset Converter — Question → Proposition")
    print("=" * 60)

    # Create output directory
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Convert MIX
    print(f"\n▶ Converting MIX dataset...")
    if not os.path.exists(INPUT_MIX):
        print(f"  ❌ Input file not found: {INPUT_MIX}")
        sys.exit(1)
    n_mix = convert_mix(INPUT_MIX, OUTPUT_MIX)
    print(f"  ✅ {n_mix} propositions → {OUTPUT_MIX}")

    # Convert PRO
    print(f"\n▶ Converting PRO dataset...")
    if not os.path.exists(INPUT_PRO):
        print(f"  ❌ Input file not found: {INPUT_PRO}")
        sys.exit(1)
    n_pro = convert_pro(INPUT_PRO, OUTPUT_PRO)
    print(f"  ✅ {n_pro} propositions → {OUTPUT_PRO}")

    print(f"\n{'=' * 60}")
    print(f"  Done! {n_mix + n_pro} total propositions converted.")
    print(f"{'=' * 60}\n")


if __name__ == "__main__":
    main()
