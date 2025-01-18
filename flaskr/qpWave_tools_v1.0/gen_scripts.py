import sys

def generate_scripts(poplist_file):
    try:
        with open(poplist_file) as f:
            pops = [line.strip() for line in f if line.strip()]
        
        for i in range(len(pops)-1):
            for j in range(i+1, len(pops)):
                pop1, pop2 = pops[i], pops[j]
                result_file = f"{pop1}-{pop2}.result"
                print(f"cd result && if [ ! -f {result_file} ]; then echo -e '{pop1}\\n{pop2}' > {pop1}-{pop2}.left && cat parqpWave.template | sed 's/replaceleft/{pop1}-{pop2}.left/g' > {pop1}-{pop2}.par && qpWave -p {pop1}-{pop2}.par > {result_file}; fi && cd ..")

    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python gen_scripts.py leftPops.txt")
        sys.exit(1)
    generate_scripts(sys.argv[1])
