import archanaSasi from '../assets/images/leaders/archana-sasi.jpg';
import kashishJaiswal from '../assets/images/leaders/kashish-jaiswal.jpg';
import syedZahidSaleem from '../assets/images/leaders/syed-zahid-saleem.jpg';
import adyaGupta from '../assets/images/leaders/adya-gupta.jpg';
import darshVithlani from '../assets/images/leaders/darsh-vithlani.jpg';
import laeeqaIffathUrRaheman from '../assets/images/leaders/laeeqa-iffath-ur-raheman.jpg';
import swapnilGhosh from '../assets/images/leaders/swapnil-ghosh.jpg';
import veeraSrinivasaRaoLachireddy from '../assets/images/leaders/veera-srinivasa-rao-lachireddy.jpg';
import agRajeshwari from '../assets/images/leaders/ag-rajeshwari.jpg';

const FACULTY_ADVISOR = {
  name: 'Dr. Archana Sasi',
  role: 'Faculty Advisor',
  year: 'Assistant Professor, Department of CSE · PhD in CSE',
  image: archanaSasi,
};

const CORE_TEAM = [
  {
    name: 'Kashish Jaiswal',
    role: 'President',
    year: '3rd Year, AIML',
    image: kashishJaiswal,
  },
  {
    name: 'Syed Zahid Saleem',
    role: 'Vice President',
    year: '2nd Year, AIML',
    image: syedZahidSaleem,
  },
  {
    name: 'Adya Gupta',
    role: 'Secretary',
    year: '2nd Year, AIML',
    image: adyaGupta,
  },
];

const LEADS = [
  {
    name: 'Darsh Vithlani',
    role: 'Tech Lead',
    year: '3rd Year, AIML',
    image: darshVithlani,
  },
  {
    name: 'K Laeeqa Iffath Ur Raheman',
    role: 'Design Lead',
    year: '3rd Year, AIML',
    image: laeeqaIffathUrRaheman,
  },
  {
    name: 'Swapnil Ghosh',
    role: 'Social Media Lead',
    year: '2nd Year, AIML',
    image: swapnilGhosh,
  },
  {
    name: 'Veera Srinivasa Rao Lachireddy',
    role: 'Marketing Lead',
    year: '2nd Year, AIML',
    image: veeraSrinivasaRaoLachireddy,
  },
  {
    name: 'A G Rajeshwari',
    role: 'Photography Lead',
    year: '2nd Year, AIML',
    image: agRajeshwari,
  },
];

function FacultyCard({ name, role, year, image }) {
  return (
    <div className="flex flex-col items-center text-center">
      <div className="w-36 h-36 md:w-40 md:h-40 rounded-full overflow-hidden border-2 border-primary-light/40 shrink-0 bg-surface mb-5">
        <img
          src={image}
          alt={name}
          className="w-full h-full object-cover"
        />
      </div>

      <div className="text-lg md:text-xl font-bold text-text">
        {name}
      </div>

      <div className="text-xs font-mono uppercase tracking-widest text-primary-light mt-2">
        {role}
      </div>

      <div className="text-sm text-text-muted mt-2 max-w-xs">
        {year}
      </div>
    </div>
  );
}

function LeaderCard({ name, role, year, image, highlight = false }) {
  return (
    <div
      className={`group border rounded-lg overflow-hidden bg-surface/60 transition-colors ${
        highlight
          ? 'border-primary-light/40 hover:border-primary-light/70'
          : 'border-border hover:border-text-dim'
      }`}
    >
      <div className="relative aspect-[4/5] bg-surface overflow-hidden">
        <img
          src={image}
          alt={name}
          className="w-full h-full object-cover"
        />
      </div>

      <div className="p-4">
        <div className="text-sm font-semibold text-text leading-tight">
          {name}
        </div>

        <div className="text-xs font-mono uppercase tracking-widest text-primary-light mt-1.5">
          {role}
        </div>

        <div className="text-xs text-text-dim mt-1">
          {year}
        </div>
      </div>
    </div>
  );
}

export default function Leaders() {
  return (
    <section id="leaders" className="relative border-b border-border">
      <div className="max-w-7xl mx-auto px-5 md:px-10 py-14 md:py-24">

        {/* section label */}
        <div className="inline-flex items-center gap-2 mb-6 px-3 py-1.5 border border-border rounded-full text-xs font-mono tracking-widest text-text-muted uppercase">
          Leadership
        </div>

        <h2 className="text-2xl sm:text-3xl md:text-4xl font-bold tracking-tight leading-tight mb-4 max-w-2xl">
          The people running things.
        </h2>

        <p className="text-sm md:text-base text-text-muted leading-relaxed max-w-xl mb-14">
          Student leaders responsible for planning, building, and running
          everything the Turing Club does.
        </p>

        {/* row 1: faculty advisor, centered, distinct circular style */}
        <div className="flex justify-center mb-10 sm:mb-14">
          <FacultyCard {...FACULTY_ADVISOR} />
        </div>

        {/* row 2: president, vice president, secretary */}
        <div className="grid grid-cols-3 gap-3 sm:gap-5 max-w-3xl mx-auto mb-6 sm:mb-8">
          {CORE_TEAM.map((leader) => (
            <LeaderCard key={leader.name} {...leader} />
          ))}
        </div>

        {/* row 3: all leads */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-3 sm:gap-5">
          {LEADS.map((leader) => (
            <LeaderCard key={leader.name} {...leader} />
          ))}
        </div>

      </div>
    </section>
  );
}