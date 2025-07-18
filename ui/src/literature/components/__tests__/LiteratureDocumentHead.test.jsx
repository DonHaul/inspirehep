import React from 'react';
import { render } from '@testing-library/react';
import { fromJS } from 'immutable';
import { Helmet } from 'react-helmet';

import LiteratureDocumentHead from '../LiteratureDocumentHead';

describe('LiteratureDocumentHead', () => {
  it('renders with only title', () => {
    render(
      <LiteratureDocumentHead
        metadata={fromJS({
          titles: [
            { title: 'The title', subtitle: 'the subtitle which we dont care' },
            { title: 'Second title which we dont care' },
          ],
        })}
        created="2019-01-16T00:00:00+00:00"
      />
    );

    const helmet = Helmet.peek();
    const title = helmet.title.join('');
    expect(title).toEqual('The title - INSPIRE');
  });

  it('renders full literature', () => {
    const metadata = fromJS({
      abstracts: [
        { value: 'First abstract is important' },
        { value: 'Second, not so much' },
      ],
      titles: [{ title: 'Test Title' }],
      authors: [
        { full_name: 'Test, Author' },
        { full_name: 'Another, Author' },
      ],
      arxiv_eprints: [{ value: '1910.06344' }],
      dois: [{ value: '12.1234/1234567890123_1234' }],
      citation_pdf_urls: [
        'https://fulltext.cern/pdf/1',
        'https://fulltext.cern/pdf/2',
      ],
      publication_info: [
        {
          journal_title: 'Test Journal',
          journal_issue: 'test issue',
          journal_volume: '3',
          page_start: '12',
          page_end: '22',
          year: '1983',
        },
        { journal_title: 'Test Jornal 2 (which will not be used)' },
      ],
    });

    render(
      <LiteratureDocumentHead
        metadata={metadata}
        created="2019-01-16T00:00:00+00:00"
      />
    );

    const helmet = Helmet.peek();
    const title = helmet.title.join('');
    expect(title).toEqual('Test Title - INSPIRE');
  });
});
