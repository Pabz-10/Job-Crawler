import { useState } from 'react';
import jobsData from './jobs.json';
import './index.css';

function App() {
  const [jobs, setJobs] = useState(jobsData || []); // Use jobsData directly, with a fallback for safety
  const [sortConfig, setSortConfig] = useState({ key: 'date', direction: 'descending' });
  const [locationFilter, setLocationFilter] = useState('All');

  const sortedJobs = [...jobs].sort((a, b) => {
    if (a[sortConfig.key] < b[sortConfig.key]) {
      return sortConfig.direction === 'ascending' ? -1 : 1;
    }
    if (a[sortConfig.key] > b[sortConfig.key]) {
      return sortConfig.direction === 'ascending' ? 1 : -1;
    }
    return 0;
  });

  const filteredJobs = sortedJobs.filter(job => {
    if (locationFilter === 'All') {
      return true;
    }
    return job.location.toLowerCase().includes(locationFilter.toLowerCase());
  });

  const requestSort = (key) => {
    let direction = 'ascending';
    if (sortConfig.key === key && sortConfig.direction === 'ascending') {
      direction = 'descending';
    }
    setSortConfig({ key, direction });
  };

  const getSortIndicator = (key) => {
    if (sortConfig.key !== key) return null;
    return sortConfig.direction === 'ascending' ? ' ▲' : ' ▼';
  };

  return (
    <>
      <h1>New Grad & Junior Developer Roles</h1>
      <div className="filters">
        <span>Filter by location: </span>
        <button onClick={() => setLocationFilter('All')} className={locationFilter === 'All' ? 'active' : ''}>All</button>
        <button onClick={() => setLocationFilter('Toronto')} className={locationFilter === 'Toronto' ? 'active' : ''}>Toronto</button>
        <button onClick={() => setLocationFilter('Vancouver')} className={locationFilter === 'Vancouver' ? 'active' : ''}>Vancouver</button>
        <button onClick={() => setLocationFilter('Burnaby')} className={locationFilter === 'Burnaby' ? 'active' : ''}>Burnaby</button>
      </div>
      <p>Showing {filteredJobs.length} roles. Click table headers to sort.</p>
      <table>
        <thead>
          <tr>
            <th onClick={() => requestSort('title')}>Title{getSortIndicator('title')}</th>
            <th onClick={() => requestSort('company')}>Company{getSortIndicator('company')}</th>
            <th onClick={() => requestSort('location')}>Location{getSortIndicator('location')}</th>
            <th onClick={() => requestSort('date')}>Date{getSortIndicator('date')}</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody>
          {filteredJobs.map((job, index) => (
            <tr key={index}>
              <td>{job.title}</td>
              <td>{job.company}</td>
              <td>{job.location}</td>
              <td>{job.date}</td>
              <td><a href={job.link} target="_blank" rel="noopener noreferrer">Apply on {job.site}</a></td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}

export default App;
