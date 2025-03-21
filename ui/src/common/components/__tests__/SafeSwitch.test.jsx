import { render } from '@testing-library/react';
import { Route } from 'react-router-dom';
import { MemoryRouter } from 'react-router-dom';
import SafeSwitch from '../SafeSwitch';

describe('SafeSwitch', () => {
  it('renders childrens and redirect to errors', () => {
    const Foo = () => <div>Foo Component</div>;
    const { asFragment } = render(
      <MemoryRouter>
      <SafeSwitch>
        <Route path="/foo" component={Foo} />
      </SafeSwitch>
      </MemoryRouter>
    );
    expect(asFragment()).toMatchSnapshot();
  });
});
