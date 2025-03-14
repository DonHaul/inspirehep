import React, { useMemo } from 'react';

import LiteratureSearchContainer from '../../literature/containers/LiteratureSearchContainer';
import { AUTHOR_PUBLICATIONS_NS } from '../../search/constants';
import AssignViewContext from '../AssignViewContext';
import AssignViewOwnProfileContext from '../assignViewOwnProfileContext';
import AssignViewDifferentProfileContext from '../assignViewDifferentProfileContext';
import AssignViewNoProfileContext from '../assignViewNoProfileContext';
import AssignViewNotLoggedInContext from '../assignViewNotLoggedInContext';
import AssignDrawerContainer from '../containers/AssignDrawerContainer';

function AuthorPublications({
  authorFacetName,
  assignView,
  assignViewOwnProfile,
  assignViewDifferentProfile,
  assignViewNoProfile,
  numberOfSelected,
  assignViewNotLoggedIn,
}: {
  authorFacetName: string;
  assignView: boolean;
  assignViewOwnProfile: boolean;
  assignViewDifferentProfile: boolean;
  assignViewNoProfile: boolean;
  assignViewNotLoggedIn: boolean;
  numberOfSelected: number;
}) {
  const baseQuery = useMemo(
    () => ({
      author: [authorFacetName],
    }),
    [authorFacetName]
  );
  const baseAggregationsQuery = useMemo(
    () => ({
      author_recid: authorFacetName,
    }),
    [authorFacetName]
  );

  return (
    <AssignViewNotLoggedInContext.Provider value={assignViewNotLoggedIn}>
      <AssignViewNoProfileContext.Provider value={assignViewNoProfile}>
        <AssignViewDifferentProfileContext.Provider
          value={assignViewDifferentProfile}
        >
          <AssignViewOwnProfileContext.Provider value={assignViewOwnProfile}>
            <AssignViewContext.Provider value={assignView}>
              <LiteratureSearchContainer
                namespace={AUTHOR_PUBLICATIONS_NS}
                baseQuery={baseQuery}
                baseAggregationsQuery={baseAggregationsQuery}
                noResultsTitle="0 Research works"
                embedded
                numberOfSelected={numberOfSelected}
                page="Author publications"
              />
              {assignView && <AssignDrawerContainer />}
            </AssignViewContext.Provider>
          </AssignViewOwnProfileContext.Provider>
        </AssignViewDifferentProfileContext.Provider>
      </AssignViewNoProfileContext.Provider>
    </AssignViewNotLoggedInContext.Provider>
  );
}

export default AuthorPublications;
