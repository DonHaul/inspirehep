import React from 'react';
import { render } from '@testing-library/react';
import { fromJS } from 'immutable';

import ThesisInfo from '../ThesisInfo';

describe('ThesisInfo', () => {
  it('renders full thesis info', () => {
    const thesisInfo = fromJS({
      degreeType: 'phd',
      date: '11-11-2011',
      defense_date: '12-12-2012',
      institutions: [
        {
          name: 'Institution 1',
        },
      ],
    });
    const { asFragment } = render(<ThesisInfo thesisInfo={thesisInfo} />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('renders with defense date', () => {
    const thesisInfo = fromJS({
      date: '11-11-2011',
      defense_date: '12-12-2012',
    });
    const { asFragment } = render(<ThesisInfo thesisInfo={thesisInfo} />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('renders with date and without defense date', () => {
    const thesisInfo = fromJS({
      date: '11-11-2011',
    });
    const { asFragment } = render(<ThesisInfo thesisInfo={thesisInfo} />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('renders without any date', () => {
    const thesisInfo = fromJS({
      institutions: [
        {
          name: 'Institution 1',
        },
      ],
    });
    const { asFragment } = render(<ThesisInfo thesisInfo={thesisInfo} />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('renders empty if null', () => {
    const { asFragment } = render(<ThesisInfo />);
    expect(asFragment()).toMatchSnapshot();
  });
});
