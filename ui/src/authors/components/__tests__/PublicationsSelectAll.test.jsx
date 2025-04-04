import React from 'react';
import { render } from '@testing-library/react';
import { fromJS, Set, List } from 'immutable';

import PublicationsSelectAll from '../PublicationsSelectAll';

describe('PublicationsSelectAll', () => {
  it('renders checked if all publications are part of the selection', () => {
    const publications = fromJS([
      {
        metadata: {
          control_number: 1,
        },
      },
      {
        metadata: {
          control_number: 2,
        },
      },
    ]);
    const selection = Set([1, 2]);
    const { asFragment } = render(
      <PublicationsSelectAll
        publications={publications}
        selection={selection}
        onChange={jest.fn()}
      />
    );
    expect(asFragment()).toMatchSnapshot();
  });

  it('renders disabled', () => {
    const { asFragment } = render(<PublicationsSelectAll disabled />);
    expect(asFragment()).toMatchSnapshot();
  });

  it('render unchecked if all publications are not part of the selection', () => {
    const publications = fromJS([
      {
        metadata: {
          control_number: 1,
        },
      },
      {
        metadata: {
          control_number: 2,
        },
      },
    ]);
    const selection = Set([2]);
    const { asFragment } = render(
      <PublicationsSelectAll
        publications={publications}
        selection={selection}
        onChange={jest.fn()}
      />
    );
    expect(asFragment()).toMatchSnapshot();
  });

  it('calls onChange with publication ids when checkbox change', () => {
    const publications = fromJS([
      {
        metadata: {
          control_number: 1,
          curated_relation: false,
          can_claim: true,
        },
      },
      {
        metadata: {
          control_number: 2,
          curated_relation: false,
          can_claim: false,
        },
      },
    ]);
    const onChange = jest.fn();
    const selection = Set([2]);
    const { getByRole } = render(
      <PublicationsSelectAll
        publications={publications}
        selection={selection}
        onChange={onChange}
      />
    );
    getByRole('checkbox').click();
    expect(onChange).toHaveBeenCalledWith(
      List([1, 2]),
      List([false, false]),
      List([true, false]),
      true
    );
  });
});
